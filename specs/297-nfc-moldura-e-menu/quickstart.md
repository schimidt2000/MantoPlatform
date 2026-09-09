# Quickstart — como validar a feature 297 de ponta a ponta

Guia de validação, não de implementação. O que cada passo prova está na coluna da direita.

## Pré-requisitos

| Item | Como conferir | Se faltar |
|---|---|---|
| `ffmpeg` e `ffprobe` no PATH | `ffmpeg -version` | Instale; nesta máquina veio pelo WinGet (build LGPL) |
| `libopenh264` no ffmpeg local | `ffmpeg -encoders \| grep openh264` | O ffmpeg local **não tem `libx264`** (pegadinha registrada na 265). O código escolhe o encoder disponível; a produção usa `libx264` |
| `manto_local` no ar | `.local-db-url` existe | `scripts/db/refresh-local-db.ps1` |
| Migration aplicada | `flask db heads` bate com a revisão da feature | `flask db upgrade` |

**Aviso que vale mais que os outros**: o `manto_local` desta máquina está velho — tem **1 tag NFC e
nenhuma entrega**, contra 35 tags e 10 vídeos da produção. Ele não reproduz o defeito relatado. Todo
o `verify_297.py` cria as próprias fixtures descartáveis e não depende de nada que já esteja lá.

Toda invocação de Python que chama `create_app()` vai com as três travas:

```bash
DATABASE_URL="$(cat .local-db-url)" FLASK_ENV=development MANTO_SEM_THREADS=1 python <script>
```

Sem `MANTO_SEM_THREADS=1` sobem as threads de fundo — inclusive a nova, que começaria a converter
vídeo de verdade no seu laptop. Sem `FLASK_ENV=development` o espelho manda e-mail e escreve no
Google Agenda da empresa.

## 1. A verificação automática

```bash
DATABASE_URL="$(cat .local-db-url)" FLASK_ENV=development MANTO_SEM_THREADS=1 \
  python specs/297-nfc-moldura-e-menu/verify_297.py
```

Quinze cenários, descritos na tabela da spec. Saída esperada: `15/15`. Os cenários 7, 8 e 12
**precisam** falhar do lado do servidor (recado inválido, leitura sem permissão e segundo envio com
a fila ocupada) — se passarem, o verify está quebrado, não o código.

O script gera o vídeo de teste na hora com `ffmpeg`, então ele demora cerca de um minuto. Ele limpa
tudo no `finally`, inclusive os arquivos que criou em `instance/nfc_media/`.

## 2. Os portões da casa

```bash
cd frontend && npm run typecheck
```

```bash
ruff check app/impressoes3d/video_ops.py app/impressoes3d/nfc_ops.py app/impressoes3d/nfc_recados_ops.py app/api/nfc_read.py app/api/nfc_write.py app/models.py app/__init__.py
```

Os dois limpos. `ruff format` só nos arquivos novos.

## 3. A tela pública, que é o coração da feature

Suba o backend e o app público, e abra `/nfc/<code>` de uma tag de teste **em viewport mobile
375x812**:

| Cena | O que precisa acontecer |
|---|---|
| Capa | Um botão só, grande, sobre o céu estrelado. Nada toca sozinho |
| Abertura | O toque inicia o vídeo **com som**. Existe "pular" visível o tempo todo |
| Menu | Três botões, todos acima da dobra, alvo de toque ≥ 44px. Sem rolagem horizontal de 320 a 430px |
| Mensagem especial | O vídeo abre em pé, ocupando a coluna, com transição suave e caminho de volta |
| Recado | Enviar mostra agradecimento sem sair da página. Texto vazio destaca o campo |
| Segunda visita | Recarregue: a capa não aparece mais, o menu abre direto |
| Movimento reduzido | Com "reduzir movimento" ligado no sistema, nada pisca nem desliza, e tudo continua alcançável |
| Código inventado | `/nfc/01-XXXXXX` mostra o menu genérico, sem o botão da mensagem, sem erro |

A cena de abertura só existe se houver vídeo de abertura cadastrado. Sem ele, a página abre no menu —
e isso também precisa ser conferido.

## 4. O gerenciador

Em `/3d/tags?aba=videos`:

- Os cards mostram o vídeo **em pé**, não espremido em 16:9.
- Enviar um vídeo grande: a barra de progresso anda, o card aparece como "preparando", e vira
  "pronto" sozinho, sem recarregar a página.
- A caixinha "Aplicar a moldura da Manto" já vem marcada. Desmarcar e enviar produz vídeo sem
  moldura.
- Sem moldura cadastrada, o envio com a caixa marcada avisa e entrega mesmo assim.
- Um recado enviado pela página pública aparece na tag e toca o sino.

## 5. A prova de que o vídeo ficou leve

Depois de enviar um vídeo 4K pelo ERP, sonde o arquivo entregue:

```bash
ffprobe -v error -show_entries stream=width,height -show_entries format=size,duration -of default=noprint_wrappers=1 instance/nfc_media/<arquivo>.mp4
```

Esperado: `width=1080`, altura par, e `size` na casa de 15 MB por 30 segundos. Compare com o arquivo
que você enviou.

Há uma prova de bancada pronta em `scratchpad/prova_moldura.py`, usada na Fase 0: ela gera um 4K
sintético, aplica uma moldura de tamanho diferente e confere que a borda mudou e o miolo não.

## 6. Os dez vídeos que já estão em produção

Só depois do merge, e só pelo dono, no **Shell do Render** (o classificador bloqueia scripts por
SSH), fora do horário da equipe:

```bash
cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask nfc-reprocessar
```

Sem `--execute` ele lista o que faria, com o tamanho de antes, e não escreve nada. Só então,
com `--execute`. Um vídeo por vez; dá para parar no meio, porque cada entrega é
independente e o arquivo velho só é apagado depois que o novo existe.

Depois, a sonda de sempre para confirmar que a produção está viva:

```bash
curl -s https://app.mantoproducoes.com.br/api/formularios/comum/schema
```

## 7. O que NÃO se prova aqui

- **Que a cliente em 4G assiste sem travar.** Isso se confere no celular, com dados móveis, abrindo
  uma tag real. O número de 15 MB é a razão de acreditar que vai funcionar, não a prova.
- **Que o `ffmpeg` continuará existindo no contêiner.** Ele não está declarado no `render.yaml`
  (dívida registrada em `docs/05`). O código degrada com segurança, mas quem confere é o deploy.
