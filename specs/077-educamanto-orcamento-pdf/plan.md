# Implementation Plan: Gerar orçamento PDF no EducaManto + histórico (077)

**Branch**: `077-educamanto-orcamento-pdf` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Botão "Gerar orçamento" no EducaManto: escolhe pacotes, gera um PDF com **uma página por pacote**
(nome, explicação fixa por nome, dias, VALOR SEM/COM NF, formas de pagamento), reproduzindo a
estrutura do PDF de referência. Os valores vêm do motor da tela (congelados). Histórico próprio dos
orçamentos gerados (lista + baixar de novo), no estilo da calculadora. **Migration manual** (nova
tabela de histórico).

## Decisões (research)

- **Pacotes = Master/Intermediário/Básico** (escolha do cliente). Explicação **fixa por nome** (mapa
  constante). Sem novo campo no pacote.
- **PDF reconstruído** com reportlab (o arquivo de referência é um exemplo preenchido, com
  placeholders — sobrepor colidiria). Reaproveita a técnica/identidade do `orcamento/pdf.py` (cores
  Manto). Tenta embutir o logo extraído do PDF de referência; senão, cabeçalho textual.
- **Valores congelados**: o motor JS calcula sem/com NF por pacote (com transporte da feature 076);
  o cliente envia os valores; o servidor guarda o snapshot e renderiza o PDF — re-render idêntico no
  histórico (não recalcula com preços futuros), coerente com o `result_snapshot` da calculadora.
- **Histórico próprio** (`EducaMantoQuote`), separado do `OrcamentoHistory` (campos diferentes).

## Data model

`educamanto_quotes`: `id`, `user_id` (FK users, indexado), `created_at`, `client_name` (nullable),
`packages_label` (String — nomes p/ a lista), `snapshot` (Text JSON: d1, d2, ensemble, transporte
{total,label,kmT,pessoas}, packages [{id,name,sem_nota,com_nota}]).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; reportlab + pypdf (já usados); Jinja2 + JS.

**Storage**: PostgreSQL/SQLite. **Migration manual** (cria `educamanto_quotes`).

**Testing**: contra **`manto_local`** — gerar PDF (N páginas = N pacotes) via test client; conferir
que o snapshot/valores batem com o motor; histórico lista e re-baixa; ruff sem erros novos.

**Constraints**: reutilizar pdf/identidade; valores idênticos à tela; pt-BR; injeção JSON segura;
perfis do EducaManto.

**Scale/Scope**: `models.py` (+EducaMantoQuote), 1 migration, `educamanto/pdf.py` (novo),
`educamanto/routes.py` (gerar + histórico + re-download), `educamanto/index.html` (botão+modal+JS),
`templates/educamanto/historico.html` (novo).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Técnica de PDF e identidade do orçamento; motor de cálculo
  da própria tela (fatorado em `valoresPacote`).
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Cálculo atual intacto (fatoração com paridade); nova
  tabela isolada. Verificação em `manto_local`.
- **Migrations manuais**: ✅ escrita à mão.

**Resultado**: PASS — com migration manual.

## Complexity Tracking

> PDF reconstruído (não sobreposto) por o arquivo de referência ser exemplo preenchido; documentado.
