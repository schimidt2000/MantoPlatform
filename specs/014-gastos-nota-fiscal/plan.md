# Implementation Plan: Nota Fiscal obrigatória no gasto extra

**Branch**: `014-gastos-nota-fiscal` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

## Summary

No formulário de gastos extras: renomear o anexo "Comprovante" → "Nota Fiscal", torná-lo
**obrigatório** (validado no servidor e no navegador) e exibir uma orientação curta. A lista passa
a rotular a coluna como "Nota Fiscal". Sem mudança de banco; reaproveita o anexo existente.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2).
**Storage**: nenhuma migration — o anexo já é salvo em `receipt_path`; muda só rótulo/obrigatoriedade.
**Constraints**: obrigatório só para novos registros; validação no servidor; resto do fluxo intacto.
**Scale/Scope**: validação em `gastos/routes.py` (`novo`) + ajustes de texto/required no template
`gastos/index.html`.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reaproveita o campo de anexo e o fluxo existentes.
- **II. Padrões Python** ✅ — uma validação curta no `novo`.
- **III. Camadas** ✅ — obrigatoriedade na rota; rótulo/orientação no template.
- **IV. Não quebrar** ✅ — gastos antigos intactos; sem migration; demais campos inalterados.
- **V. UI/UX (pt-BR)** ✅ — rótulo claro + orientação curta; aviso amigável quando faltar.
- **VI. Planejar antes de codar** ✅ — este plano. Requisito claro, sem clarificações.

## Project Structure

```text
app/
├── gastos/routes.py            # novo: exigir anexo (Nota Fiscal) antes de criar; flash se faltar
└── templates/gastos/index.html # label "Nota Fiscal" + orientação + required no input;
                                #   coluna da lista "Comprovante" → "Nota Fiscal"
```

## Design Detalhado

### 1. Servidor (`gastos/routes.py` → `novo`)
- Após validar descrição/valor, validar o anexo: `receipt_path = _save_receipt(request.files.get("receipt"))`.
  Se `receipt_path is None` → `flash("Anexe a Nota Fiscal (foto ou PDF que mostre o valor dos produtos).", "error")`
  e `redirect(url_for("gastos.index"))` — **antes** de criar o gasto.
- Ordem: mover o `_save_receipt(...)` para junto das validações iniciais, garantindo que nada é
  persistido sem anexo. Resto inalterado.

### 2. Template (`gastos/index.html`)
- Campo de anexo: label "Comprovante (recomendado)" → **"Nota Fiscal *"**; adicionar `required` no
  `<input type="file">`; trocar a dica por:
  "Pode ser a nota escaneada ou uma foto da Nota Fiscal que mostre o valor dos produtos.
  Comprovante/cupom fiscal não serve."
- Cabeçalho da coluna na lista: "Comprovante" → "Nota Fiscal" (o link de "Ver" continua igual).

### Verificação (app real)
- Tentar registrar sem anexo → gasto não criado + aviso (servidor).
- Registrar com anexo → criado (pendente) e Nota Fiscal acessível.
- Form mostra rótulo "Nota Fiscal" + orientação; lista mostra coluna "Nota Fiscal".

### Fora de escopo
- Inspecionar/validar o conteúdo do arquivo (se é realmente NF) — é orientação ao usuário.
- Exigir Nota Fiscal retroativa em gastos já existentes.
