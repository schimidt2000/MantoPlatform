# Implementation Plan: Local do ensaio e da maquiagem no portal e na mensagem copiada

**Branch**: `093-local-ensaio-maquiagem` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/093-local-ensaio-maquiagem/spec.md`

## Summary

Garantir que o **local do ensaio** e o **local da maquiagem** apareçam tanto no **portal do artista**
quanto na **mensagem de convite copiada** (`buildWAMsg`), cada um apenas quando preenchido. A lacuna
concreta é o **local do ensaio ausente na mensagem copiada**: hoje a mensagem inclui data/horário do
ensaio e os materiais, mas não o local. O local da maquiagem já está na mensagem e ambos os locais já
estão no portal — o trabalho protege esse comportamento contra regressão e fecha a única lacuna.

Abordagem técnica: trabalho puramente de template Jinja2 + JavaScript no cliente. Exportar o local do
primeiro ensaio como uma constante JS (espelhando `_makeupLoc`) e adicioná-lo à seção "Ensaio" da
mensagem, condicionado à existência do valor.

## Technical Context

**Language/Version**: Python 3.x (Flask) + Jinja2 + JavaScript vanilla (sem framework)

**Primary Dependencies**: Flask, SQLAlchemy (nenhuma dependência nova)

**Storage**: PostgreSQL (produção) / SQLite (dev). Sem alteração de schema — usa campos existentes
(`CalendarEvent.location` do ensaio e `CalendarEvent.makeup_location` do evento).

**Testing**: pytest contra `manto_local` (Postgres). Verificação principal é de renderização de
template; teste de fumaça garante que a string do local do ensaio chega ao HTML renderizado.

**Target Platform**: Web (navegador desktop/mobile do casting e do artista)

**Project Type**: Web application (Flask monolito com templates Jinja2)

**Performance Goals**: N/A (renderização de template, sem custo perceptível)

**Constraints**: A montagem da mensagem é feita no cliente (clipboard do navegador); os dados são
injetados no template no servidor. Manter o padrão de emojis por codepoint (`E(...)`) já usado para
evitar corrupção de encoding no Windows.

**Scale/Scope**: Mudança localizada em 1 template (`app/templates/event_detail.html`); verificação de
não-regressão em `app/templates/portal/home.html`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Simplicidade**: mudança mínima, sem novo modelo, serviço ou rota. ✅
- **Sem duplicação de lógica**: reutiliza o mesmo padrão de `_makeupLoc` (ícone de local + linha
  condicional). ✅
- **Separação de responsabilidades**: lógica de apresentação fica no template; nenhum acesso novo a
  banco. ✅
- **Sem segredos/strings mágicas novas**: usa rótulos já existentes. ✅
- **Não quebrar o que funciona**: comportamento atual (maquiagem na mensagem, ambos no portal) é
  preservado e coberto por verificação. ✅

Resultado: PASS (nenhuma violação; tabela de complexidade não necessária).

## Project Structure

### Documentation (this feature)

```text
specs/093-local-ensaio-maquiagem/
├── spec.md              # Especificação
├── plan.md              # Este arquivo
├── tasks.md             # Saída do /speckit-tasks
└── checklists/
    └── requirements.md  # Checklist de qualidade da spec
```

### Source Code (repository root)

```text
app/
├── templates/
│   ├── event_detail.html        # ALTERA: exporta _ensaioLoc e adiciona linha de local na seção Ensaio
│   └── portal/
│       └── home.html            # VERIFICA: local de ensaio e maquiagem já exibidos (não-regressão)
└── models.py                    # SEM ALTERAÇÃO (campos location / makeup_location já existem)
```

**Structure Decision**: Monolito Flask existente. A feature é uma alteração de template no fluxo de
casting (`event_detail.html`) com verificação de paridade no portal (`portal/home.html`). Nenhuma
camada de serviço/repositório envolvida.

## Implementation Approach

1. **Exportar o local do primeiro ensaio** como constante JS no bloco `{% if event.ensaios %}` de
   `event_detail.html`, ao lado de `_ensaioDate/_ensaioStart/_ensaioEnd`:
   - `const _ensaioLoc = {{ (first_ensaio.location or "") | tojson }};`
   - No ramo `{% else %}`, definir `const _ensaioLoc = "";` para evitar `ReferenceError`.
2. **Adicionar a linha de local** na seção "Ensaio" de `buildWAMsg`, espelhando a maquiagem:
   - `if (_ensaioLoc) msg += \`${em.local} Local: ${_ensaioLoc}\n\`;`
   - Posicionar logo após a linha de horário do ensaio e antes dos materiais.
3. **Verificar o portal** (`portal/home.html`): confirmar que o local do ensaio (cartões de convite
   pendente e próximos eventos) e o local da maquiagem continuam exibidos e condicionais. Ajustar
   apenas se houver inconsistência (esperado: nenhuma mudança).

## Complexity Tracking

> Sem violações de constituição. Nenhuma complexidade a justificar.
