# Implementation Plan: Unificar "Log Agenda" e "Sync Agenda"

**Branch**: `002-unifica-log-sync` | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-unifica-log-sync/spec.md`

## Summary

Hoje há três entradas no menu relacionadas: **"Log Agenda"** ([base.html:42](../../app/templates/base.html#L42))
que só redireciona para `/admin/logs?entity_type=agenda`, **"Logs"** (auditoria geral) e
**"Sync Agenda"** ([base.html:203](../../app/templates/base.html#L203) → `/admin/sync`).
A "Log Agenda" é apenas o log geral pré-filtrado — redundante e fora do padrão.

**Abordagem**: a página **"Sync Agenda"** (`/admin/sync`) vira a página unificada: além do
status de sincronização e ações que já tem, ganha uma seção **"Log recente da agenda"**
(recorte de `AuditLog` com `entity_type='agenda'`) e um link para o log completo. Removemos
o item de menu "Log Agenda", apontamos a URL antiga `/agenda/log` para a página unificada,
e apagamos o template órfão `agenda_log.html`.

## Technical Context

**Language/Version**: Python 3.11+ (Flask)
**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (nenhuma nova)
**Storage**: SQLite/PostgreSQL. Sem mudança de schema, sem migration.
**Testing**: verificação manual no app real (sem suíte automatizada).
**Project Type**: web app (monólito Flask).
**Performance Goals**: a seção de log mostra um recorte recente (limitado), sem pesar a página.
**Constraints**: preservar o controle de acesso atual; não quebrar a URL antiga; sem schema.
**Scale/Scope**: mudança localizada — 1 rota admin + 1 template + 1 redirect + 1 item de menu + remover 1 órfão.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reaproveita o `AuditLog` (mesma consulta da rota
  `audit_logs`) e a página `/admin/sync` existente; a seção de log mostra um recorte e
  **linka** para o log completo (não duplica a tela de auditoria).
- **II. Padrões Python** ✅ — só uma consulta a mais na rota `sync_status`, com tipos claros.
- **III. Arquitetura em camadas** ✅ — mudança fica na rota admin + template; sem nova regra.
- **IV. Não quebrar o que funciona** ✅ — branch isolado; URL antiga redireciona (FR-005);
  controle de acesso preservado; verificação no app.
- **V. UI/UX consistente (pt-BR)** ✅ — a seção de log reusa os estilos de tabela e variáveis
  CSS já usados; textos em pt-BR; estado vazio tratado.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações.**

## Project Structure

### Source Code (arquivos afetados)

```text
app/
├── admin/
│   └── routes.py            # sync_status(): consultar AuditLog (entity_type='agenda') recente
├── calendar/
│   └── routes.py            # agenda_log(): redirect passa a apontar para /admin/sync
└── templates/
    ├── admin_sync.html      # nova seção "Log recente da agenda" + link p/ log completo
    ├── base.html            # remover item "Log Agenda" do menu; rótulo do item de sync
    └── agenda_log.html      # REMOVER (órfão)
```

**Structure Decision**: projeto Flask único. A "Sync Agenda" é a base por já conter
status + ações; só ganha a seção de log. Sem novo modelo, sem migration.

## Design Detalhado

### 1. Rota `sync_status()` (admin/routes.py)
- Após montar `months_info`, consultar as últimas ~20 entradas de `AuditLog` com
  `entity_type='agenda'` (mesma fonte e ordenação da rota `audit_logs`), passar como
  `agenda_logs` ao template.

### 2. Template `admin_sync.html`
- Nova seção "Log recente da agenda": tabela compacta (data, ator, ação, detalhe) usando
  os estilos existentes. Estado vazio: "Nenhuma atividade registrada ainda."
- Link "Ver log completo →" para `/admin/logs?entity_type=agenda`.

### 3. Menu `base.html`
- Remover o bloco do item "Log Agenda" ([base.html:41-48](../../app/templates/base.html#L41-L48)).
- Renomear o rótulo do item de sync de "Sync Agenda" para algo que comunique os dois papéis
  (ex.: "Sincronização" / "Sync & Log Agenda"). Mantém o ícone e a rota `/admin/sync`.
- O item "Logs" (auditoria geral) permanece — não é específico de agenda.

### 4. Redirect da URL antiga (calendar/routes.py)
- `agenda_log()` passa a redirecionar para `admin.sync_status` (página unificada) em vez de
  `admin.audit_logs?entity_type=agenda`. Atende FR-005 (sem links quebrados).

### 5. Limpeza
- Remover o template órfão `app/templates/agenda_log.html` (sem referências). Atende FR-007.

### Acesso
- `/admin/sync` é restrito a superadmin (`@require_superadmin`); o item "Log Agenda" também
  era só superadmin. Consolidar preserva exatamente o mesmo nível de acesso (FR-006).

### Fora de escopo
- Reescrever a página de auditoria geral (`/admin/logs`) — continua como está.
- Mudar o conteúdo/coleta dos logs.
