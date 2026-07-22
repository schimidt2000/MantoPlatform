# Contrato de API — Cadastro Público de Talentos (162)

Estende `specs/144-migracao-react-spa/contracts/api-conventions.md` e a convenção multipart de
`specs/153-upload-anexos-evento/contracts/upload-endpoints.md`, com a extensão documentada em
`research.md` §2 (múltiplos campos de arquivo distintos numa única requisição multipart).

Todas as rotas são públicas (sem `@login_required`, sem RBAC) — mesma acessibilidade do
blueprint `cadastro_bp` hoje.

## `GET /api/cadastro/check-cpf`

- Público. Rate limit: `60 per hour` por IP.
- Query: `cpf` (string, com ou sem máscara — dígitos são extraídos).
- 200 sempre: `{"exists": bool, "valid": bool}` — `valid=false` se menos de 11 dígitos
  (`exists` sempre `false` nesse caso).

## `POST /api/cadastro`

- Público. Rate limit: `10 per hour` por IP.
- `Content-Type: multipart/form-data`.
- Campos de formulário (todos como no formulário Jinja hoje): `website` (honeypot, deve vir
  vazio), `full_name`, `is_foreigner`, `cpf`, `phone_ddi`, `phone_national` (ou `phone` legado),
  `email`, `birth_date` (`YYYY-MM-DD` ou formato aceito por `parse_date`), `languages[]`
  (múltiplos valores mesmo nome), `skills[]` (múltiplos valores mesmo nome), `gender`,
  `gender_other`, `rg`, `race`, `height` (ex.: `"1,75"`), `clothing_top`, `clothing_bottom`,
  `shoe_size`, `passport`, `pix_key_type`, `pix_key`, `pix_key_secondary`, `worked_before`,
  `how_found_us`, `car_model`, `car_brand`, `car_year`, `car_plate`, `cnh_expiration`.
- Campos de arquivo: `photo_face` (obrigatório, JPG/PNG/WEBP, máx. 8 MB), `photo_full`
  (obrigatório, mesmas regras), `doc_photo` (obrigatório, JPG/PNG/WEBP/PDF, máx. 10 MB),
  `cnh_file` (opcional, mesmas regras de `doc_photo`).
- **Honeypot**: se `website` vier preenchido, responde **201** com o mesmo shape de sucesso
  (`{"id": null}` — não cria talento, não revela o bloqueio) — paridade com o redirect
  silencioso do Jinja para a página de confirmação.
- **400** — validação (mesma ordem/mensagens do Jinja, `app/cadastro/routes.py:148-201`):
  `{"error": {"message": "<mensagem específica>", "fields"?: {"<campo>": "<mensagem>"}}}`.
  Exemplos de mensagem: `"Informe o nome completo."`, `"Selecione o gênero."`, `"CPF inválido —
  confira os 11 dígitos."`, `"Este CPF já está cadastrado. Fale com a equipe da Manto."`,
  `"a foto do rosto: tipo não permitido (use JPG, JPEG, PNG, WEBP)."`.
- **201** — sucesso: `{"id": <talent_id>}`.

## Notas de paridade

- Mesma ordem de validação do Jinja (honeypot → obrigatórios de texto → CPF duplicado → uploads)
  — importante para que a mensagem de erro retornada seja idêntica para os mesmos dados
  inválidos.
- `check-cpf` e `POST /cadastro` reaproveitam a mesma checagem de duplicidade
  (`Talent.query.filter_by(cpf=cpf).first()`), então uma corrida entre os dois (candidato digita
  CPF novo, outra pessoa cadastra o mesmo CPF, candidato envia) ainda é pega no `POST` final —
  comportamento idêntico ao Jinja hoje (mesma janela de corrida já existe lá).
