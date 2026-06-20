# Implementation Plan: CPF do talento editável no site (apenas admin)

**Branch**: `066-cpf-editavel-admin` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/066-cpf-editavel-admin/spec.md`

## Summary

Permitir que o **super admin** edite o CPF do talento pela tela de edição, com normalização
(apenas dígitos), exigência de 11 dígitos, unicidade e auditoria. Demais editores (ex.: casting)
continuam vendo o CPF só em leitura e o servidor recusa qualquer alteração vinda deles. **Sem
migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + HTML/CSS/JS vanilla.

**Primary Dependencies**: Nenhuma nova. Reusa `importer.only_digits`, `app.utils.audit` e o gate
de papéis existente.

**Storage**: PostgreSQL (prod) / SQLite (dev). **Sem mudança de schema, sem migration.**

**Testing**: Verificação contra **`manto_local` (Postgres)**: super admin altera CPF (válido,
inválido, duplicado); não-admin é bloqueado (campo + servidor); restaurar dados.

**Target Platform**: App web (Railway), mobile-first.

**Constraints**: Edição de CPF restrita a SUPERADMIN no servidor (não só no template); CPF único;
auditar sem expor o número; pt-BR.

**Scale/Scope**: `talents/routes.py::edit_talent` (+ checagem/validação de CPF), `talent_edit.html`
(campo editável p/ admin), `is_superadmin` no contexto.

## Constitution Check

- **I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)**: ✅ Reusa `only_digits`, `audit` e o padrão de
  checagem de papel. Sem lógica nova paralela.
- **II. Padrões Python**: ✅ Validação pequena e clara no handler existente.
- **III. Arquitetura em camadas**: ✅ Validação/persistência na rota; template só decide exibir
  editável.
- **IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)**: ✅ Demais campos do form inalterados; CPF de
  não-admin segue read-only. Verificação em `manto_local`.
- **V. UI/UX consistente (pt-BR)**: ✅ Campo claro ("apenas admin"); erros amigáveis.
- **VI. Planejar antes de codar**: ✅ Este plano + research.
- **VII. Valores monetários BR**: N/A.

**Resultado**: PASS — sem violações, sem migration. (Bônus: tira a dependência de editar pelo
banco.)

## Project Structure

```text
app/
├── talents/routes.py        # edit_talent: CPF editável só p/ SUPERADMIN (only_digits, 11 dígitos, único, audit); is_superadmin no contexto
└── templates/talent_edit.html  # CPF: input editável se is_superadmin, senão disabled
```

**Structure Decision**: Monolito Flask; mudança isolada na rota e no template. Sem migration.

## Complexity Tracking

> Sem violações de constituição — seção não aplicável.
