# Implementation Plan: Cadastro Público de Talentos em React

**Branch**: `162-cadastro-publico-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/162-cadastro-publico-react/spec.md`

## Summary

Segunda fatia da US5 (Superfícies Públicas) — migra o formulário público de cadastro de
talentos (`app/cadastro`, hoje Jinja/vanilla, sem login) para o app `frontend/apps/public`
(já configurado desde a 161: Tailwind, TanStack Query, react-router, `@manto/api-client`,
`@manto/ui`), consumindo 2 endpoints JSON novos em `app/api/cadastro_write.py` (submissão
multipart + checagem de CPF). Toda a lógica de negócio (parsing de telefone/altura/passaporte,
normalização de tags, validação de upload, honeypot, rate limit) é copiada do módulo Jinja
existente — zero regra nova. A rota Jinja `/cadastro/*` continua no ar em paralelo até este
slice estar validado (mesmo critério da 161 para o catálogo).

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript 5.7 (frontend)

**Primary Dependencies**: Flask + SQLAlchemy + Flask-Limiter (reaproveitados, zero dependência
nova no backend). Frontend: React 18 + Vite + react-router-dom + TanStack Query + Tailwind CSS +
`@manto/ui` + `@manto/api-client` — todas já instaladas em `apps/public` desde a 161. Nenhuma
dependência nova, exceto um componente de upload de arquivo novo em `@manto/ui` (não existe
ainda no design system — primeiro formulário público a receber arquivos).

**Storage**: PostgreSQL (`manto_local` para verificação) — mesma tabela `Talent` já existente,
nenhum campo/migration novo. Arquivos via `app/storage.save_file` (local em dev, S3/R2 em
produção), mesmo helper já usado pelo Jinja.

**Testing**: script com `Flask test client` contra `manto_local` (paridade Jinja×API,
requests fora de `app.app_context()`); `tsc --noEmit` + `vite build` no frontend.

**Target Platform**: navegador (mobile-first, 320–430px), sem autenticação.

**Project Type**: web (Flask API + SPA React, monorepo `frontend/`).

**Performance Goals**: sem meta numérica nova — mesma carga que a tela Jinja atual atende hoje.

**Constraints**: uploads multipart com múltiplos campos de arquivo distintos numa única
requisição (rosto, corpo inteiro, documento, CNH opcional) — extensão da convenção multipart da
feature 153 (lá, cada endpoint recebia um único arquivo; aqui, um único endpoint recebe até 4
arquivos nomeados). Ver `research.md` §2.

**Scale/Scope**: 1 tela principal (formulário, com componente de upload novo), 1 tela de
confirmação, 2 endpoints JSON (submissão + checagem de CPF).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: zero regra de negócio nova — os 2 endpoints reaproveitam literalmente as
  mesmas funções já escritas em `app/cadastro/routes.py` e `app/talents/importer.py`
  (`_build_phone`, `_height_to_cm`, `_validate_upload`, `_yes_no`, `parse_date`,
  `normalize_tags`, `only_digits`, `_parse_passport_status`) e `app/storage.save_file`.
  Componentes `@manto/ui` (`Button`, `Card`, `Input`) são reaproveitados; só o componente de
  upload de arquivo é novo (não existe outro igual no design system — primeiro caso de upload
  em `apps/public`/`apps/internal` via componente compartilhado).
- **II (padrões de código)**: endpoint novo em `app/api/cadastro_write.py`, type hints/
  docstring; frontend com TypeScript estrito (sem `any`), `react-hook-form` + `zod` para
  validação client-side (mesmo padrão de formulários já usados em `apps/internal`), componentes
  React pequenos por seção do formulário.
- **III (API first)**: 2 endpoints novos, 100% JSON (exceto o `Content-Type: multipart/
  form-data` da submissão, que é a única exceção já prevista pela convenção de upload da 153),
  mesmo envelope de sucesso/erro do contrato geral — a rota Jinja `/cadastro/*` segue existindo
  em paralelo só pelo motivo documentado no Summary, não por regra de negócio nova.
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmo talento resultante
  (todos os campos) entre o caminho Jinja e o caminho API, para os mesmos dados de entrada
  (incluindo os mesmos arquivos). Rota Jinja `/cadastro/*` segue funcionando sem alteração.
- **V (feedback)**: formulário usa `react-hook-form` com validação client-side espelhando as
  mensagens do backend + tratamento de erro 400 da API sem apagar o preenchimento; botão de
  envio mostra estado "Enviando..." (disabled) até a resposta chegar; skeleton/estado de
  carregamento na checagem de CPF; toasts de erro amigáveis em pt-BR.
- **VIII (mobile-first)**: superfície pública de alto tráfego externo — formulário longo com
  muitos campos e 4 uploads conferido em 320–430px antes de "pronto" (inputs de arquivo com alvo
  de toque ≥44px, teclado virtual não esconde o campo ativo, layout em coluna única).
- **IX (movimento)**: transições suaves entre seções do formulário (se dividido em passos/
  acordeões) e feedback de upload (preview de imagem aparecendo com fade) via Framer Motion,
  respeitando `useReducedMotion()`.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/162-cadastro-publico-react/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cadastro-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/cadastro_write.py                 # NOVO — POST /api/cadastro + GET /api/cadastro/check-cpf
app/api/__init__.py                       # + import de cadastro_write

frontend/packages/ui/src/components/
└── file-upload.tsx                       # NOVO — componente de upload com preview (@manto/ui)

frontend/apps/public/
├── src/
│   ├── App.tsx                           # + rotas /cadastro, /cadastro/enviado
│   ├── lib/
│   │   └── cadastro.ts                   # NOVO — hook useMutation (submissão) + useQuery (check-cpf)
│   ├── components/cadastro/
│   │   ├── CadastroForm.tsx              # NOVO — formulário completo (react-hook-form + zod)
│   │   └── CpfField.tsx                  # NOVO — campo de CPF com checagem em tempo real
│   └── pages/
│       ├── CadastroPage.tsx              # NOVO — tela do formulário
│       └── CadastroSucessoPage.tsx       # NOVO — tela de confirmação

scripts/db/verify_162_cadastro_publico_react.py  # NOVO: paridade Jinja×API (envio válido,
                                                   # campo faltante, CPF duplicado, honeypot,
                                                   # estrangeiro sem CPF)
```

**Structure Decision**: núcleo do backend fica só em `app/api/cadastro_write.py` (não em
`app/cadastro/routes.py`, que é Jinja legado intocado) — mesma leitura da 161: as funções de
validação/parsing do módulo Jinja são reaproveitadas por import direto (não duplicadas), só a
orquestração da rota (ler `request.form`/`request.files`, montar resposta JSON) é nova, pois a
rota Jinja usa `render_template`/`redirect`, não retornáveis como JSON. `frontend/apps/public`
ganha as telas de cadastro seguindo a mesma estrutura de pastas da 161 (`components/`, `pages/`,
`lib/`). Componente de upload novo entra em `@manto/ui` (não em `apps/public` isolado) porque é
genérico o bastante para ser reaproveitado por outras telas futuras da migração (ex.: upload de
foto de talento/figurino, já existente em `apps/internal` desde a 155, hoje sem componente
compartilhado — oportunidade de convergência documentada em `research.md` §3, mas fora de
escopo desta fatia tocar `apps/internal`).

## Complexity Tracking

Nenhuma violação nova.
