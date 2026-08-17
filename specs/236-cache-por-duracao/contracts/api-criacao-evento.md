# API Contracts — Feature 236: Cachê sugerido pela duração real do evento

Nenhum endpoint novo; duas mudanças aditivas e uma correção de semântica.

## POST /api/events (criação, `agenda_write.py` → núcleo em `calendar/routes.py`)

- `duracao`: passa a aceitar **qualquer inteiro ≥ 1** (string numérica, como hoje). Valor não
  numérico ou < 1 → erro de validação `{"duracao": "Duração inválida."}` (400) — antes caía
  em silêncio no índice de 1h.
- Quando `orcamento_history_id` está presente, os cachês de `cache_value`/`cache_cap` são
  **recalculados no servidor** a partir do `form_snapshot` do orçamento para a duração
  enviada (1–4h = tabela; >4h = régua). A lista `orc_caches` do corpo é ignorada nesse caso
  (fallback mantido só para chamadas sem orçamento vinculado que já enviavam cachês).
- Sem `orcamento_history_id`: comportamento atual intocado (papéis sem cap).

## GET /api/events/new/prefill

- Cada item de `caches` ganha `cache_custom` (número) quando o orçamento tem `duracao_custom`
  > 4 — informativo para a tela; a criação NÃO depende dele (recompute server-side).
- Demais campos inalterados.

## GET /api/agenda/eventos/<id> (leitura do casting)

- Sem mudança de shape — `cache_cap` já é servido. O aviso novo é derivado no cliente
  (`cache < cache_cap`).
