# Implementation Plan: Migrar Drive → volume (087)

**Branch**: `087-migrar-drive-volume` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)

## Summary

O volume já está montado em `/app/instance/uploads` = pasta de uploads, então **uploads novos já caem no
volume** organizados por subpasta (basta `USE_S3` ficar **false** em produção). O trabalho é um **comando
Flask CLI** `migrate-drive-to-volume` que baixa as fotos/documentos dos talentos hospedados no Google
Drive, salva no volume (via `save_file`, compressão + subpasta) e atualiza o link no banco. Idempotente,
resiliente a falhas, com `--dry-run`. **Sem model novo, sem migration de schema.**

## Technical Context

**Arquivo**: `app/cli.py` — novo comando registrado em `register_commands(app)` (mesmo padrão do
`compress-images` existente):

```text
flask migrate-drive-to-volume [--dry-run] [--limit N]
```

**Campos migrados** (Talent): `photo_face_path`, `photo_full_path` → subpasta `talent_photos`;
`doc_photo_path`, `cnh_file_path` → subpasta `talent_docs`.

**Seleção**: só valores que começam com `http` e contêm `googleusercontent.com` ou `drive.google.com`.
Ignora vazios, `/uploads/...` e URLs externas não-Drive.

**Extração do file_id**:
- `lh3.googleusercontent.com/d/<id>` → `<id>` (foto, imagem direta).
- `drive.google.com/...` com `open?id=<id>`, `?id=<id>` ou `/file/d/<id>/...` → `<id>` (documento).

**Download**:
- Imagem lh3: GET no próprio link (acrescenta `=s0` para resolução cheia).
- Documento Drive: GET em `https://drive.google.com/uc?export=download&id=<id>`.
- Usa `requests` (já instalado). Extensão deduzida pelo `Content-Type` da resposta
  (image/jpeg→.jpg, image/png→.png, image/webp→.webp, application/pdf→.pdf; fallback .jpg).

**Gravação**: embrulha os bytes baixados em `werkzeug.datastructures.FileStorage(BytesIO, filename)` e
chama `save_file(fs, subfolder)` — reaproveita compressão de imagem + escrita no volume (USE_S3=false) e
retorna o caminho `/uploads/<subfolder>/<uuid>.<ext>`. Atualiza o campo do Talent e faz `commit` por
talento (progresso parcial seguro).

**Resiliência/idempotência**: try/except por arquivo; em falha, mantém o link original, conta erro e
segue. Como só migra links de Drive, reexecuções pulam o que já virou `/uploads/...`. `--dry-run` apenas
conta. `--limit N` processa N arquivos (para teste).

**Saída**: progresso estilo `compress-images` (OK/ERRO/SKIP, totais ao final).

## Constitution Check

- **I. Qualidade**: comando com docstring, funções pequenas (parse_id, download, save), nomes claros.
- **IV. Não quebrar**: comando novo, isolado; só altera valores de caminho de mídia ao rodar
  explicitamente; nada do fluxo normal muda.

**Resultado**: PASS — sem migration de schema.

## Testing

Contra **`manto_local`** (USE_S3=false → grava em `instance/uploads/`):
- `--dry-run`: confere a contagem (~649 arquivos / 202 talentos) sem alterar nada.
- Parser de URL: lh3 e drive `open?id=` → file_id correto; content-type → extensão.
- Migração real com `--limit` pequeno: baixa do Drive, salva no volume, arquivo existe em disco, link do
  Talent vira `/uploads/talent_photos|talent_docs/...`; rodar de novo pula (idempotente). (Itens de teste
  podem ser revertidos ou deixados — é cópia local.)
- Falha simulada (id inválido) → mantém original, conta erro, segue.
- `ruff` sem erros novos.

> Operação em produção: `railway run flask migrate-drive-to-volume --dry-run` e depois sem `--dry-run`,
> com `USE_S3` desligado (arquivos caem no volume montado em `/app/instance/uploads`).

## Project Structure

```text
app/cli.py — novo comando migrate-drive-to-volume em register_commands()
```

## Complexity Tracking

> Sem violações. Risco: links do Drive sem permissão pública → tratados como falha (pulados/relatados).
