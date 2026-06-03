# Implementation Plan: Gastos extras abertos a todos, balanço só para admin

**Branch**: `013-gastos-todos-usuarios` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

## Summary

Relaxar a permissão da página de Gastos Extras: qualquer usuário autenticado pode **registrar** e
acessar a página. Aprovar/rejeitar continuam **só super admin**. O **balanço** (totais) e os gastos
de **terceiros** ficam visíveis só para o super admin — o usuário comum vê apenas os próprios
gastos. Sem mudança de banco.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2).
**Storage**: nenhuma migration — só muda permissão/filtragem e renderização condicional.
**Constraints**: aprovar/rejeitar negados no servidor para não-admin; super admin sem regressão.
**Scale/Scope**: 3 ajustes em `gastos/routes.py` (index, novo), 1 no menu (base.html), condicionais
no template `gastos/index.html`.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reaproveita a página, o modelo e o fluxo existentes.
- **II. Padrões Python** ✅ — mudanças pequenas e claras; sem nova lógica de negócio.
- **III. Camadas** ✅ — autorização e filtragem na rota; visibilidade no template.
- **IV. Não quebrar** ✅ — aprovar/rejeitar/excluir e impacto no balanço inalterados; super admin
  idêntico; sem migration; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — usuário comum vê formulário + "Meus gastos"; admin vê totais + tudo.
- **VI. Planejar antes de codar** ✅ — este plano; 1 decisão confirmada com o usuário.

## Decisão confirmada (AskUserQuestion)

- Usuário comum vê **apenas os próprios gastos** (não os de terceiros) + formulário; sem balanço.

## Project Structure

```text
app/
├── gastos/routes.py            # index: remove abort(403); filtra por autor p/ não-admin;
│                               #   totais só p/ super admin. novo: remove abort(403).
├── templates/
│   ├── base.html               # link "Gastos Extras": gate SUPERADMIN → autenticado
│   └── gastos/index.html       # KPIs de balanço só p/ super admin; título "Meus gastos"
│                               #   p/ não-admin; coluna "Autor" só p/ super admin
```

## Design Detalhado

### 1. Rota `index` (gastos/routes.py)
- Remover `if not _is_superadmin(): abort(403)`.
- `is_sa = _is_superadmin()`.
- Query: super admin → todos; comum → `filter_by(created_by_id=current_user.id)`.
- Totais (`total_aprovado`/`total_pendente`): calculados só se `is_sa`; senão `None`.
- `funcionarios` continua sendo passado (dropdown de reembolso disponível a todos).
- Passar `is_superadmin=is_sa` ao template (já existe).

### 2. Rota `novo` (gastos/routes.py)
- Remover `if not _is_superadmin(): abort(403)`. Resto inalterado (`created_by_id = current_user.id`,
  status "pendente", validações, desembolso, comprovante).

### 3. Rotas `aprovar`/`rejeitar`/`excluir`
- Inalteradas — já restritas no servidor (`_is_superadmin()`); `excluir` já permite autor/pendente.

### 4. Menu (base.html)
- Trocar `{% if ... eff_has_role('SUPERADMIN') %}` do item "Gastos Extras" por
  `{% if current_user.is_authenticated %}`.

### 5. Template (gastos/index.html)
- Envolver o bloco de KPIs (totais) em `{% if is_superadmin %}`.
- Título da lista: "Histórico de gastos" (admin) vs "Meus gastos" (comum).
- Coluna "Autor" (th + td) só para super admin (para o comum é sempre ele mesmo — redundante).
- Botões aprovar/rejeitar já estão sob `{% if is_superadmin %}`; manter.

### Verificação (app real)
- Usuário comum: GET 200, vê formulário, registra gasto (pendente), vê só os próprios, sem totais,
  sem aprovar/rejeitar.
- Acesso direto de não-admin a `aprovar`/`rejeitar` → 403.
- Super admin: vê totais, todos os gastos, aprova/rejeita (sem regressão).

### Fora de escopo
- Notificar admin de novos gastos; paginação/busca da lista; mudar o fluxo de pagamento.
