# Implementation Plan: Revisão de Vídeo Profissional Mobile-First

**Branch**: `104-revisao-video-mobile` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/104-revisao-video-mobile/spec.md`

## Summary

Evoluir o módulo de revisão de mídia existente (features 088/090) em três frentes:

1. **Tela do material mobile-first** — reescrever `app/templates/revisao/asset.html` com layout
   estilo Vimeo Review: player no topo (largura total no mobile), composer de comentário fixo,
   lista de comentários com abas pendentes/concluídos, alvos de toque ≥ 44px, tudo com os tokens
   do design system (`--accent`, `--panel`, `--line`, `--r-md`...).
2. **Fluxo de conclusão transparente** — `ReviewComment` ganha `resolved_by`/`resolved_at`;
   concluir mostra quem/quando para todos; permissões: concluir/reabrir = criador do espaço,
   autor do comentário ou super admin; excluir = autor ou super admin (ação secundária).
3. **Histórico de versões** — novo modelo `ReviewAssetVersion` guarda cada versão substituída
   (arquivo, autor, datas); comentários ganham `version_number`; a tela atual mostra só os
   comentários da versão vigente; versões antigas são navegáveis (leitura) até expirarem.

## Technical Context

**Language/Version**: Python 3.12 + Flask + SQLAlchemy (stack existente)

**Primary Dependencies**: Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate (Alembic).
Frontend: Jinja2 + HTML/CSS/JS vanilla (sem framework JS, sem libs novas)

**Storage**: PostgreSQL em produção (Railway) / cópia local `manto_local` para testes; arquivos
via `app/storage.py` (`save_file`/`delete_file`, Volume montado em `instance/uploads`)

**Testing**: verificação manual no app real contra `manto_local` (Postgres) via
`scripts/db/run-local.ps1` — projeto não possui suíte pytest; checagens `mypy app/`,
`ruff check/format` nos arquivos tocados

**Target Platform**: web (mobile-first ≤ 480px + desktop), navegadores móveis (Safari iOS /
Chrome Android)

**Project Type**: web app Flask monolítico com blueprints

**Performance Goals**: tela de revisão utilizável em rede móvel; lista de comentários via
fetch JSON já existente (sem tempo real)

**Constraints**: migrations escritas À MÃO (autogenerate quebrado por drift); compat total com
dados existentes (FR-017); política de expiração de 7 dias preservada (feature 090); zero
dependências JS novas

**Scale/Scope**: 1 blueprint existente (`app/revisao/`), 1 modelo novo, 2 colunas+2 em modelos
existentes, 1 template reescrito, 2 templates ajustados, 1 migration manual, cleanup estendido

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Evolui o módulo `app/revisao/` existente; reusa `save_file`/`delete_file`, `_can_view`/`_can_manage`, cleanup da feature 090, tokens CSS de `style.css`. Nenhum módulo paralelo. |
| II. Padrões Python | ✅ Type hints + docstrings Google style em tudo que for tocado; constantes no topo do módulo. |
| III. Arquitetura em camadas | ✅ Regras de permissão e versionamento ficam em funções puras no blueprint (padrão do módulo); rotas só orquestram. Sem query solta em template. |
| IV. Não quebrar o que funciona | ✅ Migration com backfill preserva dados; rotas existentes mantêm URLs; comportamento legado (imagem/PDF/áudio) preservado. Verificação no app real contra `manto_local`. |
| V. UI/UX consistente + feedback | ✅ Toda ação assíncrona com loading/erro/sucesso; botões desabilitam ao enviar (anti duplo clique); confirmação em exclusões; textos pt-BR; cores só via variáveis CSS. |
| VI. Planejar antes de codar | ✅ Este plano. |
| VII. Valores monetários BR | N/A — feature sem valores monetários. |

**Gate: PASS** (sem violações; nada em Complexity Tracking).

> Nota sobre testes: o repositório não possui diretório `tests/` (nenhuma feature anterior
> criou). O portão "testes relevantes passam" é atendido pela verificação funcional no app real
> apontando para `manto_local` (Postgres), conforme prática registrada do projeto.

## Project Structure

### Documentation (this feature)

```text
specs/104-revisao-video-mobile/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões de design técnico
├── data-model.md        # Fase 1 — modelo de dados e migration
├── quickstart.md        # Fase 1 — como rodar/verificar
├── contracts/
│   └── routes.md        # Fase 1 — contrato das rotas HTTP/JSON
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                          # ReviewAssetVersion (novo); ReviewComment += version_number,
│                                      #   resolved_by, resolved_at; ReviewAsset (helpers de versão)
├── revisao/
│   ├── routes.py                      # replace snapshot de versão; comments por versão; resolve com
│   │                                  #   autoria; permissões FR-010/FR-011; visualização de versão antiga
│   └── cleanup.py                     # expira também arquivos de ReviewAssetVersion
├── templates/revisao/
│   ├── asset.html                     # REESCRITO — mobile-first estilo Vimeo (player, abas, composer fixo,
│   │                                  #   seletor/histórico de versões)
│   ├── space.html                     # ajuste leve: contadores pendentes/concluídos por material
│   └── list.html                      # sem mudança estrutural (conferir consistência visual)
└── static/style.css                   # (somente se precisar de utilitário novo; preferir <style> no template)

migrations/versions/
└── a3b4c5d6e7f8_review_versions_resolution.py   # manual; down_revision = e7b8c9d0f1a2
```

**Structure Decision**: monolito Flask existente; toda a mudança vive no blueprint
`app/revisao/`, em `app/models.py` e nos templates `app/templates/revisao/`. Sem módulos novos.

## Decisões de design (resumo — detalhe em research.md)

1. **Versões**: `ReviewAssetVersion` guarda apenas versões **anteriores** (snapshot criado no
   momento da substituição). `ReviewAsset` continua sendo a fonte da versão **atual** (campos
   `file_path`, `version`, `expires_at`, `file_removed` inalterados) → zero mudança nos fluxos
   existentes de upload/expiração/finalização e nenhum backfill de arquivos.
2. **Comentário ↔ versão**: coluna `version_number` em `review_comments` (não FK), carimbada
   com `asset.version` na criação; backfill dos existentes com a versão atual do material.
   Tela principal filtra `version_number == asset.version`; histórico filtra pelo número.
3. **Conclusão**: `resolved_by` + `resolved_at` (FK users / datetime). `resolved` (bool) é
   mantido como fonte do estado. Reabrir limpa os dois campos.
4. **Visualização de versão antiga**: mesma rota `asset_view` com query param `?v=N` —
   renderiza o arquivo da versão antiga (se não expirado) em modo somente leitura (composer
   oculto, banner de aviso).
5. **Expiração de versões antigas**: cada snapshot herda o `expires_at` que tinha quando era
   atual; `cleanup_expired_review_files()` passa a varrer também `review_asset_versions`.
   Finalizar/excluir material remove também os arquivos das versões antigas.
6. **Mobile-first**: CSS mobile como base + `@media (min-width: 900px)` para duas colunas;
   player `position: sticky` no topo no mobile; composer em barra fixa inferior
   (`position: sticky; bottom: 0`) que convive com o teclado virtual; time code capturado no
   `focus` do textarea (congela o instante); alvos de toque ≥ 44px.

## Complexity Tracking

Sem violações da constituição — tabela não aplicável.
