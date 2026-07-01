# Implementation Plan: Duração de 3 horas na calculadora de orçamentos

**Branch**: `098-orcamento-duracao-3h` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/098-orcamento-duracao-3h/spec.md`

## Summary

Adicionar a duração de **3 horas** à calculadora de orçamentos. Hoje cada preço/coeficiente é uma tripla
**[1h, 2h, 4h]** (índices 0/1/2) espalhada por config, cálculo, histórico e criação de evento. A mudança
transforma tudo em **quádrupla [1h, 2h, 3h, 4h]** (índices 0/1/2/3), com o valor de **3h derivado por
média entre 2h e 4h** (editável). O ponto de maior risco é que o **4h deixa de ser o índice 2 e passa a
ser o índice 3** — todas as referências a "índice 2 = 4h" precisam virar índice 3.

## Technical Context

**Language/Version**: Python 3.x (Flask), Jinja2, JS vanilla

**Primary Dependencies**: Flask, SQLAlchemy, Flask-Migrate (Alembic). Sem dependência nova.

**Storage**: PostgreSQL (prod) / SQLite (dev). Preços em `SiteSetting.pricing_config` (JSON) — migração
automática no `load()` (sem DDL). `OrcamentoHistory` ganha coluna **`total_3h`** → migração manual
(down_revision `b4e5f6a7c8d9`). Testar contra `manto_local`.

**Testing**: pytest/scripts contra `manto_local`. Casos: 3h = média(2h,4h); config antiga (3 valores) →
injeta 3h; cálculo com 3h; histórico grava total_3h; criação de evento por 3h.

**Target Platform**: Web (área comercial / configurações)

**Project Type**: Web app (monolito Flask + Jinja2 + JS)

**Constraints**: Refatoração pervasiva de índices — cuidado com **índice 2 (antes 4h, agora 3h)** vs
**índice 3 (4h)**. Migração automática da config salva sem perder valores. Não quebrar orçamentos antigos.
Escopo = `app/orcamento` (o `Manto_Sales/` separado fica fora).

**Scale/Scope**: ~15 laços `range(3)`→`range(4)` no cálculo; DEFAULTS + `_migrate` em settings.py;
pricing.py; 1 migração; 3-4 templates; orcamento.js; mapeamentos de duração na criação de evento.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Sem duplicação**: a lógica de derivação (média 2h/4h) fica centralizada num helper em settings.py e é
  reusada pela migração e pelos DEFAULTS. ✅
- **Não quebrar o que funciona**: migração automática injeta 3h em config antiga; `total_3h` nullable;
  orçamentos antigos seguem válidos. ✅
- **Sem segredos novos**; migração manual conforme padrão do projeto. ✅
- **Money-critical**: verificação numérica explícita (3h entre 2h e 4h) contra `manto_local`. ✅

Resultado: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/098-orcamento-duracao-3h/
├── spec.md
├── plan.md
├── tasks.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
app/
├── orcamento/
│   ├── settings.py     # DEFAULTS → 4 valores; _migrate injeta 3h (média) em arrays de tamanho 3;
│   │                   #   helper interpolar_3h(); load POST de settings lê range(4)
│   ├── pricing.py      # range(3) → range(4) em aplicar_markup e afins
│   └── routes.py       # cálculo: range(3)→range(4); índice 4h 2→3; dur_labels/incluir/show/_idx/
│                       #   _pix_durs/session/history com 3h; settings POST lê _3; total_3h no histórico
├── models.py           # OrcamentoHistory.total_3h (Numeric nullable)
├── calendar/routes.py  # _compute_performer_caches: cache_3h; prefill total_3h; dur map {"3":2}, 4h→3;
│                       #   duracao_custom not in (1,2,3,4)
└── templates/orcamento/
    ├── index.html      # checkbox/label/total de 3h; custom_valor/mult_3h; textos "1h/2h/3h/4h"
    ├── resultado.html  # exibe 3h
    └── settings.html   # colunas 3h (range(3)→range(4) + cabeçalhos)
static/js/orcamento.js  # cálculos client-side de 3h (base, totais, personalizado)

migrations/versions/
└── <hash>_orcamento_total_3h.py   # add column orcamento_history.total_3h (down_revision b4e5f6a7c8d9)
```

**Structure Decision**: Mantém a arquitetura atual (config JSON + funções de pricing + rota de cálculo +
templates + JS). A introdução do 3h é uma expansão de dimensão (3→4) com um único ponto de derivação
(`interpolar_3h`) reutilizado pela migração de config e pelos DEFAULTS.

## Implementation Approach (phased)

1. **Config/derivação (US2)**: `interpolar_3h(v2,v4)` (média, arredondada); DEFAULTS com 4 valores;
   `_migrate` insere 3h no índice 2 de todo array de tamanho 3 (recursivo pelas tabelas: markup, ator,
   cantor, tecnico_som, coordenador, especiais/variantes). `pricing.py` `range(3)`→`range(4)`.
2. **Cálculo (US1)**: em `routes.py`, todos os `range(3)`→`range(4)`; toda referência "índice 2 = 4h"
   vira índice 3; adicionar 3h a `dur_labels`, `incluir` (default), `show`, `_idx`, `_pix_durs`,
   `total_custom` (excluir 3 do custom), sessão e mensagem.
3. **Persistência (US3)**: `OrcamentoHistory.total_3h` + migração; gravar `total_3h=totals[2]`,
   `total_4h=totals[3]`. Ajustar `session["orcamento_quote"]` (`total_3h`, `show_3h`).
4. **Settings UI + POST**: settings.html com coluna 3h (`range(4)` + cabeçalhos); POST em routes lê os 4
   índices por tabela.
5. **Calculadora UI + JS**: index.html (checkbox "3 horas", labels, total-3h, custom_*_3h); resultado.html
   exibe 3h; `orcamento.js` replica os cálculos client-side para 4 durações.
6. **Criação de evento (US3)**: `_compute_performer_caches` inclui `cache_3h`; prefill lê `total_3h`;
   `dur_idx`/`duracao` mapeiam "3"→índice 2 e "4"→índice 3; `duracao_custom not in (1,2,3,4)`.
7. **Verificação** contra `manto_local`: números do 3h entre 2h e 4h; config antiga migrada; histórico
   grava total_3h; criação por 3h.

## Complexity Tracking

> Sem violações de constituição. A complexidade é de *volume* (muitos pontos), não de arquitetura;
> mitigada por um único helper de derivação e verificação numérica.
