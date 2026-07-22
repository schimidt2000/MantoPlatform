# Data Model: Cadastro Público de Talentos em React

Nenhum campo ou tabela novos. O endpoint cria um `Talent` (`app/models.py`) exatamente com os
mesmos campos já preenchidos pelo handler Jinja (`app/cadastro/routes.py:211-248`):

| Campo | Origem | Observação |
|---|---|---|
| `full_name` | `full_name` | obrigatório |
| `cpf` | `cpf` (dígitos) | `None` se `is_foreigner` |
| `is_foreigner` | `is_foreigner` | checkbox |
| `artistic_name` | `artistic_name` | opcional |
| `phone` | `_build_phone(form)` | DDI + nacional |
| `email_contact` | `email` | obrigatório |
| `birth_date` | `parse_date(birth_date)` | obrigatório |
| `rg` | `rg` | obrigatório |
| `gender` | `gender` (ou `gender_other` se "Outro") | obrigatório |
| `race` | `race` | obrigatório |
| `languages` | `languages[]` unidos por vírgula | ≥1 obrigatório |
| `skills` | `skills[]` unidos por vírgula | ≥1 obrigatório |
| `tags` | `normalize_tags(skills)` | derivado |
| `height_cm` | `_height_to_cm(height)` | obrigatório |
| `clothing_size_top` / `clothing_size_bottom` | form | obrigatórios |
| `shoe_size` | form | obrigatório |
| `passport_status` / `passport_visa_text` / `has_visa` | `_parse_passport_status(passport)` | obrigatório |
| `pix_key` / `pix_key_type` / `pix_key_secondary` | form | tipo+chave obrigatórios |
| `worked_before` | `_yes_no(worked_before)` | opcional |
| `how_found_us` | form | opcional |
| `car_model` / `car_brand` / `car_year` / `car_plate` | form | opcionais |
| `cnh_expiration` | `parse_date(cnh_expiration)` | opcional |
| `cnh_file_path` | upload `cnh_file` → `save_file` | opcional |
| `photo_face_path` | upload `photo_face` → `save_file` | obrigatório |
| `photo_full_path` | upload `photo_full` → `save_file` | obrigatório |
| `doc_photo_path` | upload `doc_photo` → `save_file` | obrigatório |
| `status` | fixo `"pending"` | — |
| `source` | fixo `"public_form"` | — |

Validações de obrigatoriedade/formato são as mesmas já em vigor (`app/cadastro/routes.py:148-
201`), apenas retornadas como JSON (`{"error": {"message", "fields"?}}`) em vez de re-renderizar
o template com `error=msg`.
