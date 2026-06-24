# Implementation Plan: Formulário público de cadastro (086)

**Branch**: `086-cadastro-publico-talento` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)

## Summary

Novo **blueprint público** `cadastro_bp` (`/cadastro`) com formulário próprio (mesmas perguntas do
Google Form), uploads via a camada `save_file` (disco em dev / S3-R2 em produção), criando um **Talent
pendente** (`source="public_form"`). Limites de tamanho/tipo por arquivo, rate-limit e honeypot.
Whitelist de `/cadastro` no `portal_domain_routing` para abrir em `portal.mantoproducoes.com.br/cadastro`.
**Sem model novo, sem migration** (reusa `Talent`).

## Technical Context

**Novos arquivos**:
- `app/cadastro/__init__.py` — pacote.
- `app/cadastro/routes.py` — `cadastro_bp` (url_prefix `/cadastro`):
  - `GET /cadastro` → `cadastro/form.html`.
  - `POST /cadastro` → valida, salva arquivos, cria `Talent(status="pending", source="public_form")`,
    redireciona para `/cadastro/enviado`. `@limiter.limit("10 per hour")`.
  - `GET /cadastro/enviado` → `cadastro/success.html`.
- `app/templates/cadastro/form.html` — página **standalone** (não estende `base.html`), mobile-first,
  seções, marcadores de obrigatório, dicas de tamanho, preview de imagem, estado "enviando…" + trava de
  duplo envio, honeypot oculto.
- `app/templates/cadastro/success.html` — confirmação.

**Reuso**:
- `app/talents/importer.py`: `only_digits`, `parse_date`, `normalize_tags`, `_parse_passport_status`.
- `app/storage.py`: `save_file(file, subfolder)` (compressão + local/S3).
- `app/__init__.py`: registrar `cadastro_bp`; adicionar `/cadastro` aos prefixos liberados em
  `portal_domain_routing`.

**Validação de arquivo** (helper em routes):
- Fotos (rosto/corpo): ext em {jpg,jpeg,png,webp}, ≤ 8 MB.
- Documentos (doc/CNH): ext em {jpg,jpeg,png,webp,pdf}, ≤ 10 MB.
- Tamanho via `file.seek(0,2); size=file.tell(); file.seek(0)`. Excedeu/ext inválida → erro amigável,
  re-render preservando campos de texto.

**Campos** (mesma origem da importação): full_name*, artistic_name, phone*, email*, birth_date*, cpf*
(≥11 dígitos, único), rg, gender, race, languages, skills (+ tags via `normalize_tags`), height
("1,75"→cm), clothing_top, clothing_bottom, shoe_size, passport (select→`_parse_passport_status`),
pix_key, pix_key_type, pix_key_secondary, worked_before, how_found_us, car_* (opc.), cnh_expiration +
cnh_file (opc.), photo_face*, photo_full*, doc_photo*. (* = obrigatório.)

**Segurança**: rate-limit no POST; honeypot (`website`) → se preenchido, finge sucesso sem criar;
`strip()` nos textos; CPF normalizado; duplicado bloqueado.

## Constitution Check

- **I. Qualidade**: helpers com type hints/docstrings; lógica de arquivo isolada; reuso de importer.
- **III. Camadas**: route fina chamando `save_file`/helpers; sem query crua espalhada.
- **IV. Não quebrar**: blueprint novo + 2 linhas em `__init__` (registro + whitelist); nada existente
  muda de comportamento.

**Resultado**: PASS — sem migration.

## Testing

Contra **`manto_local`** (USE_S3=false → grava em `instance/uploads/`):
- `GET /cadastro` retorna 200 sem login e contém as seções/campos.
- `POST /cadastro` com CPF de teste único + 3 imagens pequenas → cria `Talent` pendente
  (`source="public_form"`), com `photo_face_path/photo_full_path/doc_photo_path` preenchidos e arquivos
  gravados; depois **remover** o talento e arquivos de teste.
- CPF duplicado → não cria, mostra erro.
- Arquivo grande / ext inválida → rejeitado.
- Honeypot preenchido → "sucesso" sem criar.
- `portal_domain_routing`: host do portal + `/cadastro` **não** redireciona para `/portal/`.
- `ruff` sem erros novos.

## Project Structure

```text
app/cadastro/__init__.py
app/cadastro/routes.py
app/templates/cadastro/form.html
app/templates/cadastro/success.html
app/__init__.py            — registra cadastro_bp + whitelist /cadastro no portal_domain_routing
```

## Complexity Tracking

> Sem violações. Maior risco é o tamanho do template; mitigado por seções claras e reuso de helpers.
