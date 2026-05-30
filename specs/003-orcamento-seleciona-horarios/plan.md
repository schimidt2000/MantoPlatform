# Implementation Plan: Selecionar quais durações entram no orçamento

**Branch**: `003-orcamento-seleciona-horarios` | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-orcamento-seleciona-horarios/spec.md`

## Summary

O orçamento gera 3 durações fixas (1h/2h/4h) que aparecem em 3 saídas: a **mensagem de
WhatsApp** ([orcamento/routes.py:_process_quote](../../app/orcamento/routes.py)), o **resumo
de valores** ([resultado.html](../../app/templates/orcamento/resultado.html)) e o **PDF**
([orcamento/pdf.py](../../app/orcamento/pdf.py)). Todas leem de `session["orcamento_quote"]`.

**Abordagem**: adicionar checkboxes no formulário (1h/2h/4h, marcadas por padrão); em
`_process_quote()`, ler a seleção e gravar flags `show_1h/show_2h/show_4h` no quote da sessão;
mensagem, resumo e PDF passam a iterar apenas pelas durações marcadas. A duração extra
(custom) segue como está.

## Technical Context

**Language/Version**: Python 3.11+ (Flask)
**Primary Dependencies**: Flask, Jinja2, reportlab/pypdf (PDF) — nenhuma nova
**Storage**: sessão (`session["orcamento_quote"]`). Sem mudança de schema.
**Testing**: verificação manual no app real (sem suíte automatizada).
**Project Type**: web app (monólito Flask).
**Constraints**: sem regressão para quem não mexe nas caixas (padrão = todas); custom intacto.
**Scale/Scope**: 4 arquivos — form, gerador, template de resultado, PDF.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reaproveita a estrutura do quote em sessão e o
  helper `_dur_block`; apenas filtra por seleção. Sem duplicar lógica de preço.
- **II. Padrões Python** ✅ — refator pequeno e localizado; tipos preservados.
- **III. Arquitetura em camadas** ✅ — mudança fica no gerador (rota) + templates + PDF; sem
  nova regra de negócio de precificação.
- **IV. Não quebrar o que funciona** ✅ — padrão = todas marcadas (idêntico ao atual);
  fallback para "todas" se vier vazio; branch isolado; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — checkboxes com variáveis CSS, marcadas por padrão, rótulos pt-BR.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações.**

## Project Structure

### Source Code (arquivos afetados)

```text
app/
├── orcamento/
│   ├── routes.py        # _process_quote(): ler seleção; filtrar mensagem + pix_vista; gravar flags no quote
│   └── pdf.py           # gerar_orcamento_pdf(): renderizar só as durações marcadas (investimento + PIX)
└── templates/
    └── orcamento/
        ├── index.html      # checkboxes "Incluir no orçamento" (1h/2h/4h), marcadas por padrão
        └── resultado.html  # KPIs do resumo só para durações marcadas + colunas dinâmicas
```

**Structure Decision**: projeto Flask único; mudança localizada no módulo de orçamento.

## Design Detalhado

### Contrato de dados (session["orcamento_quote"])
Acrescentar três flags booleanas: `show_1h`, `show_2h`, `show_4h`. (O custom já é controlado
por `total_custom`.) Assim, as três saídas (mensagem, tela, PDF) compartilham a mesma decisão.

### 1. Formulário ([index.html](../../app/templates/orcamento/index.html))
- Novo bloco "Incluir no orçamento" (perto do bloco de duração), com 3 checkboxes
  `name="incluir_duracao"` valores `1h`/`2h`/`4h`, todas com `checked`.

### 2. Gerador (`_process_quote`)
- `incluir = request.form.getlist("incluir_duracao")`; se vazio → `["1h","2h","4h"]` (FR-005,
  back-compat). Derivar `show_1h/2h/4h`.
- Refatorar a montagem de `investimento`: construir lista `[(label, total)]` só com as
  durações marcadas e juntar (helper `_dur_block` reaproveitado).
- Refatorar `pix_vista`: incluir só as linhas das durações marcadas.
- Gravar `show_1h/show_2h/show_4h` no `session["orcamento_quote"]`.

### 3. Resultado ([resultado.html](../../app/templates/orcamento/resultado.html))
- Envolver cada KPI (1h/2h/4h) em `{% if quote.show_1h %}` etc.
- Tornar `--cols` dinâmico: contar as durações visíveis + custom.

### 4. PDF ([pdf.py](../../app/orcamento/pdf.py))
- Montar a lista de durações do "Investimento" só com as marcadas (usando as flags do quote).
- Idem para as linhas de PIX à vista.

### Compatibilidade
- Quote antigo na sessão sem as flags: tratar `quote.get("show_1h", True)` como `True`
  (default), garantindo que orçamentos já gerados não quebrem.

### Fora de escopo
- Tornar a duração extra (custom) selecionável por checkbox (segue incluída quando informada).
- Mudar preços/markup ou o histórico persistente.
