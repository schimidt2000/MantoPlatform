# Contrato de Rotas — Dispensar Tarefa de Casting (108)

Blueprint `calendar_bp` (já registrado sem prefixo, ex.: `/events/...`, `/agenda`). Rotas
novas no nível raiz do blueprint — sem prefixo de evento, porque agem sobre o cargo
diretamente.

## `POST /roles/<int:role_id>/dismiss`

**Auth**: `@login_required` + `_is_superadmin()` — caso contrário `abort(403)`.

**Body**: nenhum campo obrigatório (form vazio; o `role_id` já está na URL).

**Comportamento**:
1. Busca `EventRole.query.get_or_404(role_id)`.
2. Se `role.talent_id is not None` → `flash("Só é possível dispensar cargos sem talento
   atribuído.", "error")` e redireciona sem alterar nada (FR-009).
3. Se já dispensado (`dismissed_at is not None`) → idempotente, apenas redireciona (sem
   duplicar log) — cobre clique duplo (edge case da spec).
4. Caso contrário: `dismissed_at = datetime.utcnow()`, `dismissed_by = current_user.id`;
   grava `EventLog` (`event_id=role.event_id`, mensagem `f"Dispensou tarefa de casting:
   {role.character_name}"`, `actor_role="Casting"`); `db.session.commit()`;
   `flash("Tarefa dispensada.", "success")`.
5. Redireciona para `request.referrer` se presente e local, senão `url_for("home")`.

**Resposta**: sempre `302` (padrão do módulo — forms tradicionais, sem modo JSON).

## `POST /roles/<int:role_id>/restore`

**Auth**: idêntico ao dismiss.

**Comportamento**:
1. Busca `EventRole.query.get_or_404(role_id)`.
2. Se não estava dispensado → idempotente, apenas redireciona.
3. Caso contrário: limpa `dismissed_at`/`dismissed_by`; grava `EventLog` (mensagem
   `f"Restaurou tarefa de casting: {role.character_name}"`); commit; flash de sucesso.
4. Redireciona para `request.referrer` (fallback home).

## Home (`GET /`) — dados adicionais no contexto do template

Quando `is_superadmin` (variável já calculada na rota):

```python
dismissed_casting = (
    EventRole.query.filter(EventRole.dismissed_at.isnot(None), not_presence)
    .join(CalendarEvent)
    .filter(exclude_ensaios, future_events)
    .order_by(EventRole.dismissed_at.desc())
    .all()
)
```

Passado ao template como `dismissed_casting` (lista vazia quando não superadmin — economiza
a query fora do caso de uso).

## UI (`home.html`, seção Casting)

- Cada linha de `pending_casting`: botão adicional `Dispensar` (só quando `is_superadmin`),
  form `POST /roles/{{ r.id }}/dismiss`, `onsubmit="return confirm('Dispensar esta tarefa de
  casting? Ela deixa de aparecer como pendente — mesmo após uma nova sincronização com o
  Google Agenda.')"`.
- Sub-bloco "🗂 N dispensada(s)" (só quando `is_superadmin and dismissed_casting`): cada item
  mostra personagem, evento, "por {{ nome }} em {{ data }}" e botão `Restaurar`
  (`POST /roles/{{ r.id }}/restore`).
