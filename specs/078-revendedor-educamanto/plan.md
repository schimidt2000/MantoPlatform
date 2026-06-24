# Implementation Plan: Revendedor EducaManto + acréscimo + taxa interna (078)

**Branch**: `078-revendedor-educamanto` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Novo perfil **REVENDEDOR_EDUCAMANTO** restrito (agenda view-only + EducaManto) via guarda central;
botão **limpar transporte**; **acréscimo do vendedor** (R$) somado ao valor final = comissão do
vendedor (no total do PDF); antiga comissão do pacote vira **taxa interna**, escondida na calculadora
e customizável no cadastro. **Sem migration** (reusa o role no banco, seedável; sem novo modelo).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy; Jinja2 + JS.

**Storage**: sem migration. Novo role é criado via `seed.py` (roda no deploy). O acréscimo entra no
snapshot do orçamento (077, campo Text — sem alterar schema).

**Testing**: contra **`manto_local`** — revendedor-only acessa /agenda e /educamanto, é bloqueado em
/financeiro,/talents,/admin,/ etc., e não edita eventos; limpar transporte zera; acréscimo soma ao
final e ao PDF; package_form mostra "Taxa interna". `ruff` sem erros novos.

**Constraints**: restrição central segura (allow-list), aplicada só a revendedor-only; reuso do
EducaManto; pt-BR; sem hardcode da taxa interna.

**Scale/Scope**: `constants.py`, `seed.py`, `app/__init__.py` (before_request guard + flag de nav +
home redirect), `templates/base.html` (nav), `educamanto/routes.py` (_CAN_USE + acréscimo no
snapshot), `educamanto/pdf.py` (acréscimo no total — já via valores recebidos), `educamanto/index.html`
(limpar transporte + acréscimo + esconder taxa interna), `educamanto/package_form.html` (relabel).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Reusa motor/transporte/PDF do EducaManto, RBAC e seed
  existentes.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Restrição só p/ revendedor-only; demais perfis intactos;
  verificação em `manto_local`.
- **VI. Segurança**: ✅ Guarda central allow-list + edição já gated; perfil não entra em nenhum
  `_CAN_EDIT`.
- **VII. Valores BR**: ✅ Acréscimo com máscara R$.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/constants.py                 # RoleName.REVENDEDOR_EDUCAMANTO
seed.py                          # get_or_create_role("REVENDEDOR_EDUCAMANTO")
app/__init__.py                  # before_request: allow-list p/ revendedor-only; home redirect; flag nav
app/templates/base.html          # nav: revendedor-only vê só Agenda + EducaManto
app/educamanto/routes.py         # _CAN_USE += REVENDEDOR_EDUCAMANTO; acréscimo no snapshot
app/educamanto/index.html        # botão limpar transporte; campo acréscimo (=comissão); esconde taxa interna
app/educamanto/package_form.html # "Comissão do vendedor" -> "Taxa interna"
```

**Structure Decision**: Guarda central de acesso + ajustes na calculadora. Sem migration.

## Complexity Tracking

> Restrição app-wide concentrada num único `before_request` (allow-list) para evitar tocar rota a
> rota — mais seguro e revisável.
