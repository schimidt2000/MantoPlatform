# Contrato de API — convenções gerais (herdadas por todas as rotas futuras)

Ver `research.md` §3 para o raciocínio. Resumo normativo:

## Sucesso

- Recurso único: o objeto direto no corpo. `GET /api/auth/me` → `{"id": 1, "name": "...", ...}`
- Lista: `{"items": [...], "total": N}` (paginação usa `?page=`/`?per_page=` quando aplicável
  — não necessário para os endpoints da Fundação, que não paginam).
- Ação sem corpo de retorno relevante (ex.: logout): `204 No Content`.

## Erro

```json
{"error": {"message": "Mensagem amigável em pt-BR", "fields": {"email": "Campo obrigatório"}}}
```

- `fields` é opcional — presente só em erro de validação (400), com uma entrada por campo
  inválido, consumido pelo `zod`/`react-hook-form` no frontend para destacar o campo certo.
- Status HTTP: 400 (validação), 401 (não autenticado), 403 (sem permissão), 404 (não
  encontrado), 500 (erro interno — `message` genérica, nunca stack trace; erro real vai pro
  `logging` do servidor, mantendo o Princípio II/portão de qualidade já existente).

## Endpoints desta fatia (Fundação)

### `POST /api/auth/login`

- Body: `{"email": string, "password": string}`
- 200: `{"id", "name", "email", "roles", "is_superadmin"}` (mesmo shape de `/api/auth/me`) +
  `Set-Cookie` da sessão Flask-Login (HttpOnly)
- 401: `{"error": {"message": "E-mail ou senha inválidos"}}`

### `POST /api/auth/logout`

- 204, invalida a sessão do cookie atual (`logout_user()`)

### `GET /api/auth/me`

- 200: shape descrito em `data-model.md` — usuário autenticado atual
- 401: `{"error": {"message": "Não autenticado"}}` se não houver sessão válida

### `GET /api/dashboard`

- 200: shape descrito em `data-model.md` §"Resumo do dashboard" — campos presentes variam
  conforme papel do usuário autenticado (mesma lógica condicional de `has_role`/
  `is_superadmin`/`impersonate_role` hoje em `app/__init__.py`)
- 401: sem sessão válida

## Upload de arquivo (multipart/form-data)

Convenção introduzida na feature 153 (`specs/153-upload-anexos-evento/contracts/
upload-endpoints.md`), normativa para toda rota futura que receba arquivo:

- Requisição: `Content-Type: multipart/form-data`. Campos não-arquivo vão como campos de
  formulário comuns (`request.form`), junto do arquivo (`request.files`) — nunca JSON no
  mesmo corpo.
- Resposta: **inalterada** — mesmo envelope de sucesso/erro acima, mesmos códigos HTTP. Só a
  requisição muda de content-type; a resposta de um endpoint de upload é JSON como qualquer
  outro.
- Endpoint que edita/apaga sem receber arquivo novo continua `application/json` puro (ex.:
  corrigir um valor, excluir um registro) — só quem recebe arquivo na requisição usa
  multipart.

## Fora de escopo desta fatia

Contratos de CRUD de Agenda/Eventos, Talentos, Figurino, Financeiro, Catálogo etc. — cada um
definido no `/speckit-plan` da User Story correspondente (US2–US6), reaproveitando as
convenções gerais de sucesso/erro acima.
