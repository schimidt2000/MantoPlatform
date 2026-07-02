# Implementation Plan: Revisão — Progresso de Upload, Convite aos Revisores e Fix do Popup

**Branch**: `105-revisao-upload-convite` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/105-revisao-upload-convite/spec.md`

## Summary

Três entregas incrementais no módulo `app/revisao/`:

1. **Fix do popup (P1)**: em `asset.html`, a regra `.rv-modal { display: flex }` vence o
   atributo `hidden` (o `display: none` do user-agent para `[hidden]` perde para o seletor de
   classe). Corrigir com `.rv-modal[hidden] { display: none; }`.
2. **Progresso real de upload (P2)**: enviar o formulário de criação (e o de nova versão) via
   `XMLHttpRequest` com `FormData` e `xhr.upload.onprogress` (barra com % e MB reais). As
   rotas passam a responder JSON `{"redirect": url}` quando o cliente pede
   (`X-Requested-With: XMLHttpRequest`), preservando as flash messages para a página seguinte.
3. **Convite copiável (P3)**: botão "Copiar convite" na tela do espaço (mensagem pronta com
   título + link absoluto via `navigator.clipboard`, com fallback manual); redirect pós-criação
   ganha `?novo=1` para destacar o convite.

## Technical Context

**Language/Version**: Python 3.12 + Flask (stack existente)

**Primary Dependencies**: Flask, Flask-Login. Frontend: Jinja2 + JS vanilla —
`XMLHttpRequest` (único mecanismo com progresso de upload sem lib), `navigator.clipboard`
com fallback `execCommand('copy')`

**Storage**: nenhuma mudança de banco — zero migrations

**Testing**: verificação funcional com test client contra `manto_local` (Postgres) — requests
fora de `app_context` (memória: flask-test-client-app-context-leak) + verificação visual;
`ruff check` nos arquivos tocados

**Target Platform**: web mobile-first + desktop (Safari iOS / Chrome Android inclusos —
`navigator.clipboard` exige HTTPS, produção já é HTTPS; fallback cobre o resto)

**Project Type**: web app Flask monolítico

**Performance Goals**: progresso atualizado em tempo real durante upload de até 512 MB

**Constraints**: sem libs JS novas; flash messages preservadas no fluxo XHR (por isso JSON
redirect em vez de deixar o XHR seguir o 302 e consumi-las); formulário nunca perde dados em
erro (Constituição V)

**Scale/Scope**: 3 templates (`new.html`, `asset.html`, `space.html`), 1 helper JS novo
(`app/static/upload_progress.js`), ajustes em 2 rotas (`new_space`, `replace_asset`), zero
mudanças de modelo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Um único helper `uploadFormWithProgress()` em `app/static/upload_progress.js` serve os dois formulários (criação e nova versão) — sem duplicar o XHR por tela. Convite reusa `url_for(..., _external=True)` e o padrão de botões existente. |
| II. Padrões Python | ✅ Mudanças de rota mínimas com type hints/docstrings; helper `_wants_json()` no blueprint. |
| III. Arquitetura em camadas | ✅ Rotas continuam só orquestrando; nenhuma regra nova de negócio. |
| IV. Não quebrar o que funciona | ✅ Envio sem JS/sem arquivos continua pelo POST tradicional (fallback nativo: JSON só quando o header XHR está presente). Fluxo de flash/redirect preservado. Verificação contra `manto_local`. |
| V. UI/UX + feedback | ✅ É o coração da feature: progresso real, botão desabilitado durante envio (anti duplo clique), erro amigável sem limpar formulário, confirmação visual do "Copiado ✓". |
| VI. Planejar antes de codar | ✅ Este plano. |
| VII. Valores monetários BR | N/A. |

**Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/105-revisao-upload-convite/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões técnicas
├── data-model.md        # Fase 1 — sem entidades novas (registro)
├── quickstart.md        # Fase 1 — verificação
├── contracts/
│   └── routes.md        # Fase 1 — contrato das rotas (modo JSON)
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── revisao/
│   └── routes.py                      # _wants_json(); new_space e replace_asset respondem
│                                      #   {"redirect": url} p/ XHR; redirect pós-criação com ?novo=1
├── static/
│   └── upload_progress.js             # NOVO — uploadFormWithProgress(form, opts): XHR + FormData,
│                                      #   onprogress (%, MB), bloqueio do form, erro sem perder dados
└── templates/revisao/
    ├── new.html                       # barra de progresso + uso do helper
    ├── asset.html                     # fix .rv-modal[hidden]; progresso no form de nova versão
    └── space.html                     # botão "Copiar convite" + destaque quando ?novo=1
```

**Structure Decision**: tudo dentro do módulo de revisão existente + 1 arquivo JS estático
compartilhado (fonte única do upload com progresso).

## Decisões de design (detalhe em research.md)

1. **Popup**: regra CSS `.rv-modal[hidden] { display: none; }` — especificidade
   classe+atributo (0,2,0) vence `.rv-modal` (0,1,0); mantém o padrão `hidden` já usado no
   restante do template.
2. **Progresso**: `XMLHttpRequest` (fetch não expõe progresso de upload sem streams
   experimentais). Barra reutiliza tokens (`--accent`, `--line`); texto "45% — 135 MB de 300 MB".
3. **Redirect XHR**: resposta JSON `{"redirect": ...}` quando `X-Requested-With:
   XMLHttpRequest`; o cliente navega com `window.location`. Evita que o XHR siga o 302 e
   consuma as flash messages (que devem aparecer na página de destino).
4. **Fallback sem JS**: os forms mantêm `method="post"` + `enctype` e as rotas mantêm o
   comportamento 302 quando o header não está presente.
5. **Convite**: texto montado no template (título + `url_for(..., _external=True)`);
   `navigator.clipboard.writeText` com fallback de `<textarea>` selecionável; botão vira
   "Copiado ✓" por 2,5s. Destaque pós-criação via query param `?novo=1` (sem estado novo no
   banco).

## Complexity Tracking

Sem violações — tabela não aplicável.
