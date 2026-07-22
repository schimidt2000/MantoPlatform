# Data Model: Upload de Fotos e Documentos (155)

Nenhuma tabela/campo novo — reaproveita entidades já existentes (`app/models.py`). Esta fatia só
adiciona operações de escrita (upload/remover/rotacionar) sobre campos que já existiam desde
antes da migração React.

## Talent (`app/models.py:91`)

Campos de arquivo já existentes, agora editáveis pela tela React:

| Campo              | Tipo   | Formatos aceitos      | photo_type (API) |
|---------------------|--------|------------------------|-------------------|
| `photo_face_path`   | String | JPG/PNG/WEBP           | `face`            |
| `photo_full_path`   | String | JPG/PNG/WEBP           | `full`            |
| `doc_photo_path`    | String | JPG/PNG/WEBP/PDF       | `doc`             |
| `cnh_file_path`     | String | JPG/PNG/WEBP/PDF       | `cnh`             |

Cada campo guarda uma URL relativa (`/uploads/talent_photos/...` ou `/uploads/talent_docs/...`)
ou, para registros legados importados via Google Sheets/Drive, uma URL absoluta
(`https://drive.google.com/...`) — `assetUrl` no frontend já trata os dois casos (Design
Decision 5 da 154).

## FigurinoSheet (`app/models.py:352`)

| Campo            | Tipo   | Formatos aceitos | Observação                                   |
|-------------------|--------|--------------------|-----------------------------------------------|
| `photo_filename`  | String | JPG/PNG/WEBP       | Rotação só funciona se path local (`/uploads/...`) |

## Validation Rules (herdadas do comportamento Jinja atual, sem mudança)

- Extensão fora da lista aceita por campo → erro 400, nada é salvo.
- Upload bem-sucedido sempre substitui (nunca acumula) o arquivo anterior do mesmo campo.
- Remover um campo já vazio é no-op seguro (200, sem erro).
- Rotação sem foto, ou com foto em URL não-local (legado Drive), retorna erro 400 amigável —
  mesma limitação já existente na tela Jinja, não expandida nesta fatia.
