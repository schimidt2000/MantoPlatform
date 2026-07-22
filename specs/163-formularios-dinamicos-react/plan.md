# Implementation Plan: Formulários Dinâmicos Públicos em React

**Branch**: `163-formularios-dinamicos-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/163-formularios-dinamicos-react/spec.md`

## Summary

Terceira fatia da US5 (Superfícies Públicas) — migra os dois formulários públicos dinâmicos
(`/f/pre-contrato`, `/f/corporativo`, hoje Jinja em `app/formularios/routes.py`, dirigidos por
`FormFieldDefinition`) para o app `frontend/apps/public`, consumindo 2 endpoints JSON novos em
`app/api/formularios_write.py` (schema de campos + submissão). Toda a lógica de negócio (motor
dinâmico de validação/montagem de seções/mensagem de WhatsApp, vínculo automático de evento) é
reaproveitada por import direto das funções já existentes em `app/formularios/routes.py` — zero
duplicação. Como os campos são inteiramente dirigidos por dados (não há lista fixa por
formulário), o frontend ganha um componente `DynamicForm` genérico que renderiza qualquer
conjunto de campos a partir de um schema JSON. As rotas Jinja `/f/pre-contrato` e `/f/corporativo`
continuam no ar em paralelo; a área interna autenticada (`/formularios/*`) não é tocada.

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript 5.7 (frontend)

**Primary Dependencies**: Flask + SQLAlchemy + Flask-Limiter (reaproveitados, zero dependência
nova no backend). Frontend: React 18 + Vite + react-router-dom + TanStack Query + Tailwind CSS +
`@manto/ui` + `@manto/api-client` — todas já instaladas em `apps/public` desde a 161/162.
Nenhuma dependência nova.

**Storage**: PostgreSQL (`manto_local` para verificação) — mesmas tabelas `FormResponse`/
`FormFieldDefinition` já existentes, nenhum campo/migration novo.

**Testing**: script com `Flask test client` contra `manto_local` (paridade Jinja×API, requests
fora de `app.app_context()`); `tsc --noEmit` + `vite build` no frontend.

**Target Platform**: navegador (mobile-first, 320–430px), sem autenticação.

**Project Type**: web (Flask API + SPA React, monorepo `frontend/`).

**Performance Goals**: sem meta numérica nova — mesma carga que as telas Jinja atuais atendem
hoje.

**Constraints**: componente de formulário genérico — o frontend não conhece os campos em tempo
de compilação, só em tempo de execução (schema vem da API). Diferente da 162 (schema `zod`
fixo), aqui não há schema de validação client-side estático: a validação client-side real de
"campo obrigatório"/formato já não existe hoje no Jinja (só máscaras de digitação) — mantido
assim (ver `research.md` §1).

**Scale/Scope**: 2 telas públicas (pré-contrato, corporativo) reaproveitando 1 componente de
formulário genérico + 1 tela de confirmação compartilhada, 2 endpoints JSON (schema + submissão).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: zero regra de negócio nova — os 2 endpoints reaproveitam literalmente as
  funções já escritas em `app/formularios/routes.py` (`_load_fields`, `_grouped_sections`,
  `_validate_dynamic`, `_build_sections_dynamic`, `_save_response`, `_attempt_auto_link`,
  `_build_message`, `_whatsapp_link`, `_build_phone_display`, `_parse_event_date`, `FORM_META`)
  por import direto — mesmo padrão já usado pela 162 ao importar `_parse_passport_status` de
  outro módulo. Componentes `@manto/ui` (`Button`, `Card`, `Input`) reaproveitados; o componente
  `DynamicForm`/`DynamicField` é novo (não existe formulário dirigido por schema ainda no design
  system) mas fica genérico o bastante para qualquer estrutura de campo futura.
- **II (padrões de código)**: endpoint novo em `app/api/formularios_write.py`, type hints/
  docstring; frontend com TypeScript estrito (sem `any`), componentes React pequenos por tipo de
  campo.
- **III (API first)**: 2 endpoints novos, 100% JSON — as rotas Jinja `/f/pre-contrato` e
  `/f/corporativo` seguem existindo em paralelo só pelo motivo documentado no Summary, não por
  regra de negócio nova.
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesma resposta salva (mesmas
  seções/campos) e mesma mensagem de WhatsApp entre o caminho Jinja e o caminho API, para os
  mesmos dados de entrada. Rotas Jinja seguem funcionando sem alteração; área interna
  (`/formularios/*`) inteiramente intocada.
- **V (feedback)**: `DynamicForm` usa `useMutation` — botão de envio com estado "Enviando..."
  (disabled) até a resposta chegar; erro 400 nunca apaga o preenchimento, cada campo problemático
  mostra sua própria mensagem; tela de confirmação com botão de WhatsApp + abertura automática
  (paridade com `enviado.html`).
- **VIII (mobile-first)**: superfície pública de alto tráfego externo — as 2 telas conferidas em
  320–430px antes de "pronto".
- **IX (movimento)**: exibição/ocultação do campo condicional "Descreva outros" e a transição da
  tela de confirmação usam animação leve do Tailwind/Framer Motion, respeitando
  `prefers-reduced-motion`.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/163-formularios-dinamicos-react/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/formularios-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/formularios_write.py               # NOVO — GET .../schema + POST submissão
app/api/__init__.py                        # + import de formularios_write

frontend/apps/public/
├── src/
│   ├── App.tsx                            # + rotas /f/pre-contrato, /f/corporativo,
│   │                                       #   /f/:formType/enviado
│   ├── lib/
│   │   └── formularios.ts                 # NOVO — tipos do schema + hooks + máscaras
│   │                                       #   (cpf/cnpj/cep/telefone) + cliente ViaCEP
│   ├── components/formularios/
│   │   ├── DynamicField.tsx               # NOVO — despacha o widget certo por field_type
│   │   └── DynamicForm.tsx                # NOVO — busca o schema, gerencia estado/erro/envio
│   └── pages/
│       ├── FormularioPage.tsx             # NOVO — usada por ambas as rotas (formType via param)
│       └── FormularioEnviadoPage.tsx      # NOVO — confirmação + abre WhatsApp

scripts/db/verify_163_formularios_dinamicos_react.py  # NOVO: paridade Jinja×API (schema,
                                                        # submissão válida/inválida, honeypot,
                                                        # "Descreva outros", vínculo automático)
```

**Structure Decision**: núcleo do backend fica só em `app/api/formularios_write.py`, que
**importa** (não copia) as funções já existentes em `app/formularios/routes.py` — diferente da
161 (onde as queries foram copiadas porque tinham `render_template` inline) e mais parecido com
a 162 (onde a lógica pura foi extraída para um módulo `_ops`): aqui nem extração é necessária,
porque `app/formularios/routes.py` já separa 100% da lógica de negócio em funções `_`-prefixadas
puras, e só as funções de rota (`_render_public_form`, `_submit_public_form`,
`form_comum`/`submit_comum`/etc.) misturam HTTP — essas não são reaproveitadas. `frontend/apps/
public` ganha um componente de formulário genérico (`DynamicForm`/`DynamicField`), diferente do
formulário com campos fixos da 162 (`CadastroForm`), porque aqui a estrutura vem inteiramente de
dados em tempo de execução.

## Complexity Tracking

Nenhuma violação nova.
