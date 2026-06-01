# Implementation Plan: Local de saída configurável + logística no convite

**Branch**: `007-logistica-saida` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

1. **Local de saída**: novo campo `departure_location` no evento (texto), padrão "Manto
   Produções"; editável na logística; alteração notifica talentos confirmados (fluxo já existe).
2. **Convite**: `send_invite_email` passa a incluir as linhas de logística (saída horário+local,
   maquiagem horário+local) quando definidas — hoje o convite NÃO leva nenhuma logística.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2)
**Storage**: 1 coluna nova `calendar_events.departure_location` (migration à mão).
**Constraints**: padrão "Manto Produções"; sem linhas vazias no e-mail; reusar notificação de logística.
**Scale/Scope**: model + 1 handler + 1 bloco no template + e-mail de convite + migration.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reusa `_handle_save_logistics`, `_notify_accepted_roles`,
  helpers de e-mail (`_info_row`/`_info_box`). O local de maquiagem já é texto livre — espelha o padrão.
- **II. Padrões Python** ✅ — mudança pequena e tipada.
- **III. Camadas** ✅ — handler na rota; e-mail no serviço de e-mail; template só apresentação.
- **IV. Não quebrar** ✅ — coluna nullable com default na exibição; convite sem logística segue
  enviando; branch isolado; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — campo com placeholder/valor padrão "Manto Produções".
- **VI. Planejar antes de codar** ✅ — este plano.
- **Migration à mão** ✅ (autogenerate quebrado — memória do projeto).

## Project Structure

```text
app/
├── models.py                       # CalendarEvent: + departure_location (String)
├── calendar/routes.py              # _handle_save_logistics: ler/gravar departure_location + notificar
├── email_service.py                # send_invite_email: + linhas de logística (helper _logistics_rows)
└── templates/event_detail.html     # campo "Local de saída" (default Manto Produções)
migrations/versions/
└── xxxx_departure_location.py      # add_column (à mão)
```

## Design Detalhado

### 1. Model
- `CalendarEvent.departure_location = db.Column(db.String(300), nullable=True)`.
- Padrão de exibição "Manto Produções" é aplicado na leitura (template/e-mail), não no banco —
  assim eventos antigos (null) também caem no padrão sem backfill.

### 2. Migration à mão
- `down_revision` = head atual (`a7b8c9d0e1f2`). `op.add_column("calendar_events", ...)`.

### 3. Handler `_handle_save_logistics`
- Ler `departure_location` do form; `old` → comparar; se mudou e havia confirmados, entra em
  `logistics_changes` ("Local de saída: X → Y") e dispara `_notify_accepted_roles` (já existe).
- Vazio → grava None (exibição cai no padrão).

### 4. Template (event_detail.html, bloco de saída ~880)
- Adicionar input "Local de saída" com `value="{{ event.departure_location or 'Manto Produções' }}"`.
- Ajustar o label "Horário de saída da Manto" para apenas "Horário de saída" (o local agora é campo).

### 5. E-mail de convite (send_invite_email)
- Novo helper interno `_logistics_rows(event)` que monta linhas só para o que existe:
  - Saída: se `departure_time` → "Saída: {hora} — {local or 'Manto Produções'}".
  - Maquiagem: se `makeup_time` → "Maquiagem: {hora}{ — local se houver}".
- Inserir essas linhas no `rows` do convite (após Local/antes do Cachê). Sem dados → nada (FR-006).

### Verificação da US2
- Confirmar no app real que o convite renderizado contém as linhas de logística quando definidas
  e não contém quando ausentes.

### Fora de escopo
- Local de saída como seletor de endereços salvos; geocodificação do novo local para o cálculo de
  rota (o cálculo segue usando o endereço base da Manto).
