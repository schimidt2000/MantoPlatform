# Implementation Plan: Senha auto + salário comissão (084)

**Branch**: `084-criar-usuario-senha-comissao` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)

## Summary

Dois ajustes na tela **Criar Usuário** (e regra de salário compartilhada com a edição):

1. **Salário**: tornar a seção realmente opcional e habilitar **"Somente comissão"** com salário-base 0.
   Helper único `_normalize_salary(value, payment_type)` usado em `create_user` e `add_salary`.
2. **Senha de primeiro uso**: gerar uma senha forte no cliente ao carregar o formulário (modo "com
   acesso"), botão de gerar nova, e **copiar para a área de transferência ao criar**; flash informando.

**Sem model novo, sem migration.** Backend = lógica de validação; frontend = JS de geração/cópia.

## Technical Context

**Arquivos**:
- `app/admin/routes.py`
  - Novo helper `_normalize_salary(salary_value: int | None, payment_type: str) -> tuple[int, str|None]`:
    - `comissao` → `(0, None)` (salário-base 0);
    - `semanal`/`quinzenal` → exige `> 0` senão `(0, "Salário inválido.")`;
    - outro/vazio → `(0, "Selecione o tipo de pagamento.")`.
  - `_parse_salary_form`: "seção não preenchida" = sem tipo **e** salário vazio/0 → `(None, [])`
    (corrige o bug do "0,00" default); senão usa `_normalize_salary`.
  - `add_salary`: trocar a validação inline por `_normalize_salary` (mantém o fluxo de flash/redirect).
  - `create_user`: ao final do fluxo "com acesso", indicar no flash que a senha foi copiada.
- `app/templates/admin_create_user.html`
  - Campo de senha em **texto legível** + botão "🔄 Gerar nova"; gera senha no `DOMContentLoaded` se
    vazio e no modo com acesso.
  - No `submit` (modo com acesso): copiar a senha de forma **síncrona** (textarea + `execCommand('copy')`,
    com tentativa de `navigator.clipboard`), sem `preventDefault`, para concluir antes da navegação.
  - Gerador: ~12 chars, classes mistas, sem caracteres ambíguos.

**Testing**: contra **`manto_local`** —
- Salário: `_normalize_salary` e `_parse_salary_form` cobrindo: vazio→None; comissao→salary 0;
  semanal/quinzenal sem valor→erro; com valor→ok. Criar usuário comissão via test client e conferir
  `SalaryHistory(salary=0, payment_type='comissao')`.
- Senha: render do GET contém o JS de geração/cópia e o botão "Gerar nova"; campo de senha presente.
- `ruff` sem erros novos.

**Scale/Scope**: 1 rota (validação) + 1 template (JS). Sem schema.

## Constitution Check

- **I. Qualidade**: helper com type hints + docstring; lógica de validação fora do template.
- **IV. Não quebrar**: regras antigas (semanal/quinzenal exigem > 0) preservadas; só relaxa o caso
  comissão e o caso "seção vazia".

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/admin/routes.py                 — _normalize_salary(); _parse_salary_form(); add_salary(); flash
app/templates/admin_create_user.html — geração de senha + cópia no submit + botão "Gerar nova"
```

## Complexity Tracking

> Sem violações.
