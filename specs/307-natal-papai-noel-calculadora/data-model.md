# Modelo de dados — feature 307 (Phase 1)

Sem migration. Duas estruturas JSON mudam de forma aditiva.

## 1. `site_settings.pricing_config` (JSON TEXT, linha única id=1) — bloco novo

```jsonc
"datas_especiais": {
  "natal": {                                   // chave: [a-z0-9_]+, identifica a faixa no quote
    "rotulo": "Véspera e Natal",               // str ≤ 60, aparece na memória, no aviso e no resultado
    "dias": ["12-24", "12-25"],                // list[str] "MM-DD" (mês 01–12, dia válido); vale todo ano; [] = faixa desligada
    "markup": [3.34, 3.34, 3.34, 3.34],        // 4 floats em [1.0, 6.0]; substitui markup.receptivo/show
    "cache": {                                 // sobrescrita de cachê por ESPECIAL existente
      "Papai Noel":        [1000, 2000, 3000, 4000],
      "Ajudante do Noel":  [650, 1300, 1950, 2600]
    },
    "coordenador": [500, 1000, 1500, 2000],    // substitui coordenador.false E coordenador.true
    "piso":        [650, 1300, 1950, 2600],    // max(tabela, piso) para todo performer sem sobrescrita
    "nota_mensagem": "Valores especiais de 24 e 25 de dezembro."   // str ≤ 200; "" = sem nota
  }
}
```

Regras:

- `_migrate()` (em `load()`): `setdefault("datas_especiais", deepcopy(DEFAULTS[...]))`; se o valor
  salvo não for `dict`, substitui pelo padrão; cada faixa que não for `dict` ou não tiver `dias`
  lista é substituída pelo padrão da mesma chave (ou descartada, se a chave não existe nos
  DEFAULTS); listas de 3 valores passam por `_ensure4`; `cache` que não for `dict` vira `{}` e
  sobrescrita malformada (não é lista de 3/4 números) é descartada — nunca vira `[0, 0, 0, 0]`.
  **Nunca levanta** — qualquer exceção aqui devolveria os DEFAULTS do código para a tabela inteira.
- Especiais da tabela normal: DEFAULTS ganham `"Papai Noel": [712, 800, 850, 900]` e
  `"Ajudante do Noel": [423, 480, 510, 540]`. `_migrate` injeta os ausentes (regra existente,
  respeita `especiais_excluidos`) e troca "Papai Noel" **só** se `== [600, 650, 675, 700]`.
- `faixa_especial(event_date)` → `dict | None`: `{"chave", "rotulo", "dias", "markup", "cache",
  "coordenador", "piso", "nota_mensagem"}` com listas normalizadas; `None` para data vazia/inválida
  ou fora de todas as faixas. Primeira faixa que casar vence (ordem do dict); a sobrescrita de
  `cache` vale para qualquer variante do especial (simples, show ou cantor).
- `POST /api/orcamento/settings` valida antes de gravar (ver `contracts/api.md`).

## 2. `quote` (JSON em `orcamento_history.result_snapshot`) — chave nova

```jsonc
"data_especial": { "chave": "natal", "rotulo": "Véspera e Natal", "markup": [3.34, 3.34, 3.34, 3.34],
                   "nota_mensagem": "Valores especiais de 24 e 25 de dezembro." }
// ou null quando a data não cai em faixa; ausente em orçamentos salvos antes da 307.
// A nota vai junto: o PDF e o orçamento congelado não releem a tabela de preços.
```

`markup_used` passa a ser o markup efetivamente aplicado (o da faixa quando há).
`memoria` continua com os tipos `cache | subtotal | markup | pos | total`; a faixa aparece em
`detalhe`/`partes`. `form_snapshot` não muda (`event_date` já existe).

## 3. Teto de cachê das vagas (`EventRole.cache_cap` / `cache_cap_note`) — sem mudança de schema

`_compute_performer_caches(snapshot, horas_extra=None, data_evento=None)` resolve
`faixa_especial(data_evento or snapshot.get("event_date"))` e passa a faixa aos getters; o piso vale
para `ator`/`cantor`/`especial` sem sobrescrita; `cap_notes` cita o rótulo da faixa na base.

## 4. Invariantes

- Sem faixa → totais, memória, mensagem e PDF idênticos aos de hoje; `quote` ganha
  `data_especial: null`.
- Com faixa → a faixa age em cachê/markup, **antes** de brinde, noturno, técnico, maquiador,
  transporte, acréscimos e NF (a conta inversa da 305 continua válida).
- Orçamento salvo é congelado; a tabela vigente só vale para cálculos novos e para o teto no
  momento da criação/vínculo (como hoje).
