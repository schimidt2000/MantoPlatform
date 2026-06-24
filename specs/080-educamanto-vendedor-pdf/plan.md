# Implementation Plan: EducaManto vendedor + PDF (080)

**Branch**: `080-educamanto-vendedor-pdf` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Cap do acréscimo ≤ valor original (clamp + aviso); transporte sempre van c/ carretinha com
tipo/pessoas ocultos e título "(APENAS SE FOR FORA DA CIDADE DE SÃO PAULO)"; painel "Configurações do
pacote" só p/ super admin; PDF com descrição curta do tipo abaixo do título e descrição longa
(`planos.md`) após as formas de pagamento. Detecção de tipo por **substring** no nome. **Só template
+ pdf.py; sem backend/migration.**

## Technical Context

**Language/Version**: Python 3.11 (reportlab) + Jinja2/JS.

**Testing**: contra **`manto_local`** — PDF gera com as duas descrições (curta/longa) por tipo
detectado no nome; cap do acréscimo no JS; transporte usa van c/ carretinha; config oculta p/
não-admin (usa `can_manage`). `ruff` sem erros novos.

**Constraints**: uma página por pacote (descrição longa compacta); pt-BR; paridade tela/PDF.

**Scale/Scope**: `app/educamanto/pdf.py` (tipo por substring, SHORT/LONG desc, layout) e
`app/templates/educamanto/index.html` (cap, transporte fixo/oculto, título, painel só admin).

## Constitution Check

- **I. Reutilizar**: ✅ Reusa `valoresPacote`, `can_manage`, estrutura do PDF.
- **IV. Não quebrar**: ✅ Detecção por substring melhora (nomes "Tema - Tipo"); demais inalterado.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/educamanto/pdf.py
  - _tipo_for(name) por substring; SHORT_DESC (curta) + LONG_DESC (planos.md)
  - _draw_page: curta abaixo do título; longa "O QUE ESTÁ INCLUSO" após formas de pagamento
app/templates/educamanto/index.html
  - acréscimo: clamp ao valor original (valoresPacote acr=0) + aviso de máximo
  - transporte: van c/ carretinha fixo; tipo/carretinha/carros/pessoas ocultos; título novo
  - "Configurações do pacote": {% if can_manage %} (super admin)
```

**Structure Decision**: Ajustes na calculadora + enriquecimento do PDF. Sem migration.

## Complexity Tracking

> Descrição longa compacta (8.5pt) para caber na página; documentado.
