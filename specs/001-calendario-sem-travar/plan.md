# Implementation Plan: Calendário não trava mais ao abrir

**Branch**: `001-calendario-sem-travar` | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-calendario-sem-travar/spec.md`

## Summary

Hoje a rota `/agenda` ([app/calendar/routes.py:290](../../app/calendar/routes.py#L290)) tem
um "caminho rápido" (servir do banco) e um "caminho lento" (buscar no Google Calendar +
`sync_events()` + geolocalização via ViaCEP/Google Maps + limpeza), e cai no caminho lento
sempre que o mês não foi sincronizado nos últimos 15 min. Esse caminho lento bloqueia a
renderização da página fazendo N chamadas de rede — é a causa da lentidão.

**Abordagem**: inverter o padrão. A abertura do calendário passa a **sempre servir do
banco** (rápido, sem rede). A sincronização ao vivo só roda quando o usuário pede
explicitamente (`force_sync=1`, via botão "Atualizar agora"). O frescor automático
continua por conta do cron já existente (`sync_worker.py`). Adicionamos um indicador
visível de "última atualização" para dar transparência.

## Technical Context

**Language/Version**: Python 3.11+ (Flask)

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (nenhuma nova)

**Storage**: SQLite (dev) / PostgreSQL (prod). Sem mudança de schema, sem migration.

**Testing**: Verificação manual no app real (não há suíte automatizada hoje — ver constituição)

**Target Platform**: Web app (servidor Flask)

**Project Type**: Web application (projeto único, monólito Flask)

**Performance Goals**: abrir o calendário em < 1s (SC-001); zero chamadas a serviço
externo na abertura (SC-002).

**Constraints**: não regredir o sync automático em segundo plano (FR-006); não alterar
schema do banco; reutilizar o registro de frescor já existente (`SiteSetting.calendar_sync_cache`).

**Scale/Scope**: mudança localizada — 1 rota + 1 helper + 1 template. Sem novo modelo.

## Constitution Check

*GATE: precisa passar antes de implementar.*

- **I. Reutilizar antes de criar** ✅ — reaproveita `_build_events_from_db()`, o cache de
  frescor (`calendar_sync_cache`) já lido por `_is_month_fresh()`, e o `sync_events()`
  existente. Nada é duplicado.
- **II. Padrões Python** ✅ — o único código novo é um helper pequeno, com type hint e
  docstring (`_month_sync_age_minutes`).
- **III. Arquitetura em camadas** ⚠️ parcial — a mudança vive na rota (control flow). A
  lógica pesada de sync/geo permanece onde está; **extrair um `sync_service.py` está
  FORA do escopo** desta feature (é a dívida técnica já registrada na auditoria, vira
  feature própria). Não introduzimos nova regra de negócio na rota.
- **IV. Não quebrar o que funciona** ✅ — feito em branch isolado; cron preservado;
  verificação manual no app; mudança reversível.
- **V. UI/UX consistente (pt-BR)** ✅ — indicador de frescor com variáveis CSS, botão
  "Atualizar agora" com feedback (flash de sucesso/erro), textos em português.
- **VI. Planejar antes de codar** ✅ — este plano.

**Sem violações que exijam justificativa.** (A ressalva III é dívida pré-existente, não
introduzida por esta feature.)

## Project Structure

### Documentation (this feature)

```text
specs/001-calendario-sem-travar/
├── spec.md
├── plan.md              # este arquivo
├── tasks.md             # gerado pelo /speckit-tasks
└── checklists/
    └── requirements.md
```

### Source Code (arquivos afetados)

```text
app/
├── calendar/
│   └── routes.py        # agenda(): inverter control flow + novo helper de frescor
└── templates/
    └── calendar_list.html  # badge "última atualização" + botão "Atualizar agora"
```

**Structure Decision**: projeto Flask único existente. A feature é cirúrgica e toca só
a rota `agenda()` e o template `calendar_list.html`. Sem novos módulos, sem migration.
`data-model.md` e `contracts/` não se aplicam (sem novo modelo de dados, sem novo
endpoint — reutiliza a rota `/agenda` e seus parâmetros).

## Design Detalhado

### 1. Inverter o control flow em `agenda()`

Hoje ([routes.py:290-302](../../app/calendar/routes.py#L290-L302)):
```
if not force_sync and _is_month_fresh(ym):  →  fast path (banco)
else:                                        →  slow path (Google, bloqueante)
```

Passa a ser:
```
if force_sync:        →  slow path (Google) — só quando o usuário pede
                          após sincronizar: redirect para a URL sem force_sync
else:                 →  fast path (banco) — SEMPRE
```

- Remove-se a dependência de `_is_month_fresh` para decidir sincronizar ao abrir.
- Após `force_sync`, faz **redirect** para `/agenda?ym=...&view=...` (sem `force_sync`),
  para (a) evitar re-sincronizar em F5 e (b) renderizar pelo caminho rápido já fresco.
- Em falha do Google no `force_sync`, mantém o `flash` de aviso e ainda assim cai no
  caminho rápido (mostra o que há no banco) — atende FR-008.

### 2. Indicador de frescor

- Novo helper `_month_sync_age_minutes(ym: str) -> int | None`: lê
  `SiteSetting.calendar_sync_cache` e retorna minutos desde a última sync do mês, ou
  `None` se nunca. (Reaproveita a mesma fonte de `_is_month_fresh`/`_mark_month_synced`.)
- `agenda()` passa `sync_age_min` ao template.
- `calendar_list.html` mostra um badge: "atualizado há X min/h/d" (verde se recente,
  âmbar se desatualizado, cinza se "nunca atualizado").

### 3. Botão "Atualizar agora"

- Link/botão no topo da agenda apontando para a URL atual + `&force_sync=1`.
- Estado de carregamento simples (texto "Atualizando…" ao clicar) — feedback visual.
- Ao concluir, o redirect leva de volta à agenda fresca + `flash` "Agenda atualizada".

### Fora de escopo (viram features próprias)

- Extrair `calendar/sync_service.py` e tirar as chamadas ViaCEP/Google Maps de dentro do
  loop de sync (dívida técnica de arquitetura).
- Unificar as páginas "Log Agenda" e "Sync Agenda" + remover o template órfão.
- Sync assíncrono real em background a partir da web (exigiria fila de tarefas).
