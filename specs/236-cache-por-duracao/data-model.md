# Data Model — Feature 236: Cachê sugerido pela duração real do evento

**Sem migração** — nenhuma tabela ou coluna nova. A feature muda o VALOR que preenche campos
existentes e o shape de um payload interno.

## Campos existentes (semântica após a feature)

| Campo | Antes | Depois |
|---|---|---|
| `event_roles.cache_value` | pré-preenchido com o cachê da duração 1–4h (ou de 1h, no bug) | pré-preenchido com o cachê sugerido da duração REAL (régua >4h inclusa) |
| `event_roles.cache_cap` | teto imposto a não-superadmin, mesmo valor do prefill | idem — apenas o valor passa a ser o da duração real |

## Payload interno `caches` (prefill / criação)

Cada entrada por papel ganha uma chave opcional quando a duração é > 4h:

```jsonc
{
  "label": "Green 1",
  "cache_1h": 270, "cache_2h": 320, "cache_3h": 345, "cache_4h": 370,
  "cache_custom": 520,          // NOVO — régua da duração real (só quando horas > 4)
  "needs_makeup": true, "is_singer": false, "role_type": "character"
}
```

## Régua (fonte única em `_compute_performer_caches`)

```
sugerido(horas) = tabela[horas]                                  se 1 ≤ horas ≤ 4
sugerido(horas) = round(base_4h_sem_adicionais ÷ 4 × horas)       se horas > 4
                  + delta_make (se make) + noturno (se ≥19h)
                  + adicional_fora_sp_pp + show_customizado
```

Maquiador não escala por hora (custo por make). Técnico de som e coordenador escalam como os
demais papéis de tabela.
