# Implementation Plan: Indicar edição e ver histórico de uma avaliação

**Branch**: `011-historico-edicao-review` | **Date**: 2026-05-30 | **Spec**: [spec.md](./spec.md)

## Summary

Registrar versões da avaliação ao editar e exibir, na página do talento (visão da equipe), um
indicador "editada" + o histórico de versões. Uma versão = snapshot (nota geral, comentário,
sub-avaliações) gravado **antes** de sobrescrever, num campo JSON. `EventRating` ganha
`edited_at` e `edit_count`.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2)
**Storage**: nova tabela `event_rating_versions` + 2 colunas em `event_ratings` (migration à mão).
**Constraints**: registrar só "daqui pra frente"; edição sem mudança não gera versão; não
alterar a experiência de edição do talento.
**Scale/Scope**: model + 2 pontos de captura (submit_rating, rate_event_detail) + rota staff de
histórico + exibição em talent_detail.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — snapshot via JSON reaproveita os dados já existentes
  (EventRating + EventSubRating); não duplica tabelas espelho por categoria.
- **II. Padrões Python** ✅ — helper `_snapshot_rating(rating)` pequeno e tipado.
- **III. Camadas** ✅ — captura no fluxo de submit; exibição em rota staff + template.
- **IV. Não quebrar** ✅ — migration aditiva; sem versão = comportamento atual; edição do talento
  inalterada; branch isolado; verificação no app.
- **V. UI/UX (pt-BR)** ✅ — selo "editada" discreto + link "ver histórico".
- **VI. Planejar antes de codar** ✅ — este plano.
- **Migration à mão** ✅ (autogenerate quebrado — memória do projeto).

## Project Structure

```text
app/
├── models.py                       # EventRating: +edited_at,+edit_count; nova EventRatingVersion
├── talent_portal/routes.py         # _snapshot_rating(); gravar versao antes de sobrescrever
│                                   #   (submit_rating geral + rate_event_detail sub-avaliacoes)
├── talents/routes.py               # carregar versoes p/ given_ratings (ou rota dedicada)
└── templates/talent_detail.html    # selo "editada (data)" + bloco/historico de versoes
migrations/versions/
└── xxxx_rating_versions.py         # nova tabela + colunas (à mão)
```

## Design Detalhado

### 1. Model
- `EventRating`: `edited_at` (DateTime, null), `edit_count` (Integer, default 0).
- Nova `EventRatingVersion`: `id`, `rating_id` (FK), `snapshot` (Text/JSON), `replaced_at`
  (DateTime). Relationship `versions` em EventRating (ordenado por replaced_at desc).

### 2. Snapshot helper
```python
def _snapshot_rating(rating) -> dict:
    return {
        "score": rating.score,
        "comment": rating.comment,
        "subs": [
            {"category": s.category, "subject_talent_id": s.subject_talent_id,
             "score": s.score, "comment": s.comment}
            for s in rating.sub_ratings
        ],
    }
```

### 3. Captura de versão (antes de sobrescrever)
- Em `submit_rating` (POST), quando `existing` e o conteúdo vai mudar: gravar
  `EventRatingVersion(snapshot=json(_snapshot_rating(existing)), replaced_at=now)`, incrementar
  `edit_count`, setar `edited_at=now`. Só registra se houve mudança real (FR-006).
- Em `rate_event_detail` (POST das sub-avaliações): mesma ideia — antes de apagar/recriar os
  sub-ratings de uma avaliação já existente, snapshot da versão atual. Para evitar duplicar
  versão por causa das duas etapas (geral + detalhe) numa mesma sessão de edição, registrar
  versão apenas quando o conteúdo efetivamente difere do último snapshot.

### 4. Exibição (talents/routes.py + talent_detail.html)
- `given_ratings` passa a carregar `edited_at`, `edit_count` e as `versions`.
- No `talent_detail.html`, na lista "Avaliações gerais feitas por ...": se `edit_count > 0`,
  mostrar selo "editada · {edited_at}" e um expansor "ver histórico (N)" listando as versões
  (nota, comentário, sub-avaliações, data).

### 5. Migration à mão
- `down_revision` = head atual (`c8d9e0f1a2b3`). add_column x2 em event_ratings + create_table
  event_rating_versions.

### Verificação
- Editar 2x → edit_count=2, 2 versões, selo "editada".
- Edição sem mudança → não cria versão.
- Avaliação nunca editada → sem selo/histórico.

### Fora de escopo
- Mostrar histórico no portal do talento; comparar versões lado a lado; reverter para versão antiga.
