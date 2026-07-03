# Implementation Plan: Constituição Robusta + Auditoria Geral do Sistema

**Branch**: `107-constituicao-auditoria-sistema` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/107-constituicao-auditoria-sistema/spec.md`

## Summary

Três entregáveis:

1. **Constituição v1.3.0** (`.specify/memory/constitution.md`): portões 100% executáveis
   (remover pytest/mypy inexequíveis; formalizar a verificação funcional automatizada por
   feature contra `manto_local` com test client fora de app_context), princípios novos
   destilados das features 088–106 (migrations manuais, mobile-first para superfícies
   públicas), changelog e versão. CLAUDE.md alinhado (seções de comandos/portões).
2. **Auditoria** (`specs/107-.../auditoria.md`): varreduras mecânicas JÁ iniciadas (números
   reais abaixo) + passada dirigida por módulo; achados com módulo/severidade/esforço/status;
   backlog priorizado no mesmo arquivo.
3. **Correções US3** (violações objetivas encontradas):
   - **Moeda fora do padrão/fonte única** em 6 templates internos: `home.html` (kpi em formato
     AMERICANO), `talent_detail.html` (2× americano), `desempenho.html` (2× reinventado, sem
     decimais), `financeiro/dashboard.html` (macro local reinventada), `event_create.html`
     (5× reinventado) → tudo para o filtro `| brl`.
   - **Erros engolidos**: ~10 `except Exception` sem log (`calendar/routes.py` 1956/2021,
     `calendar/service.py` 186, `cli.py` 71, `email_service.py` 500, `models.py` 365,
     `storage.py` 201, `talents/importer.py` 34/42) + `print()` em
     `figurino/drive_service.py` 91 → logger.
   - **Duplo envio**: 45 templates têm form POST, só 16 têm proteção — auditar e proteger os
     fluxos principais lentos (criação de evento, cadastros internos, financeiro, orçamento).
   - **alert() de erro** em fluxos principais (11 ocorrências em 6 templates) → feedback
     inline onde for erro/validação; `confirm()` de confirmação simples permanece.

## Technical Context

**Language/Version**: Python 3.12 + Flask; Jinja2 + JS vanilla (stack existente)

**Primary Dependencies**: nenhuma nova; usa `app/money.py` (filtro `brl`) e `logging` padrão
do Flask (`current_app.logger`/logger de módulo)

**Storage**: zero mudanças de banco/migrations

**Testing**: script de varredura automatizada (regex: moeda americana/reinventada em
templates, `except` sem log, `print(`) + renderização das telas tocadas via test client
contra `manto_local` (requests fora de app_context)

**Target Platform**: sistema interno (desktop-first) + superfícies públicas já tratadas

**Project Type**: web app Flask monolítico

**Performance Goals**: sem impacto — mudanças de formatação, logging e JS de formulário

**Constraints**: FR-013 — nenhuma mudança de regra de negócio/fluxo/dados; logging não muda o
comportamento de recuperação dos `except`; auditoria registra e NÃO corrige o que exigir
decisão de produto (backlog)

**Scale/Scope**: constituição + CLAUDE.md; ~10 arquivos Python (logging); ~6 templates
(moeda); forms principais (duplo envio); relatório de auditoria

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Moeda → filtro `brl` existente (elimina 4 reimplementações paralelas — é a própria aplicação do princípio). |
| II. Padrões Python | ✅ Corrige justamente os `except` sem log proibidos pelo II; docstrings/type hints preservados onde tocar. |
| III. Camadas | ✅ Sem mudanças estruturais. |
| IV. Não quebrar o que funciona | ✅ Logging é aditivo; formatação muda só exibição (mesma informação); duplo envio é proteção; verificação de renderização + fluxos após cada classe. Mudança na constituição não invalida código existente (edge case da spec). |
| V. UI/UX + feedback | ✅ alert()→inline em erros; duplo envio protegido; confirmação em destrutivas. |
| VI. Planejar antes de codar | ✅ Este plano, com varreduras prévias. |
| VII. Moeda BR | ✅ Elimina TODAS as violações restantes nos templates internos. |

**Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/107-constituicao-auditoria-sistema/
├── plan.md              # Este arquivo
├── research.md          # Varreduras + decisões (números reais)
├── data-model.md        # Sem entidades — registro
├── auditoria.md         # ENTREGÁVEL US2: relatório completo + backlog priorizado
├── quickstart.md        # Roteiro de verificação
└── tasks.md             # Fase 2
```

*(contracts/ omitido — não há interface externa nova; o "contrato" é o formato do relatório,
definido em research.md)*

### Source Code (repository root)

```text
.specify/memory/constitution.md        # v1.3.0 — portões executáveis + princípios novos
CLAUDE.md                              # seções de comandos/portões alinhadas
app/
├── calendar/{routes.py, service.py}   # logging nos except silenciosos
├── cli.py, email_service.py, models.py, storage.py, talents/importer.py  # idem
├── figurino/drive_service.py          # print → logger
└── templates/
    ├── home.html, talent_detail.html, desempenho.html, event_create.html  # moeda → |brl
    ├── financeiro/dashboard.html      # macro money() delega ao |brl
    └── (forms principais)             # proteção de duplo envio + alert()→inline onde erro
```

**Structure Decision**: sem arquivos novos de código; relatório da auditoria vive na pasta da
feature e é referenciado pela memória do projeto.

## Decisões de design (detalhe em research.md)

1. **Portão de verificação novo** (constituição): "toda feature tem verificação funcional
   automatizada executada contra `manto_local` antes do merge (test client; requests fora de
   `app_context`)" — substitui o portão pytest/mypy inexequível; mypy vira recomendação até
   existir no ambiente.
2. **Moeda**: macro `money()` do dashboard passa a delegar ao `| brl` (call sites intactos);
   demais templates trocam a expressão pelo filtro diretamente.
3. **Logging**: cada `except` silencioso ganha `logger.warning/exception` com contexto mínimo
   (o que estava sendo tentado), sem alterar o fluxo de recuperação; `# noqa: BLE001` somente
   onde o broad-except é intencional e justificado.
4. **Duplo envio**: padrão mínimo já usado no projeto (onsubmit desabilita botão + texto de
   estado) aplicado aos forms principais identificados na auditoria por módulo.
5. **alert()**: análise caso a caso — confirmação simples (confirm) permanece; alert de ERRO
   em fluxo principal vira mensagem inline no padrão da tela.
6. **innerHTML (68 usos)**: risco XSS interno auditado e REGISTRADO no backlog (não corrigido
   em massa nesta feature — exige análise por tela; risco mitigado por ser área autenticada).

## Complexity Tracking

Sem violações — tabela não aplicável.
