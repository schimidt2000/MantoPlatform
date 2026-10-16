# Contratos de API — feature 307

Nenhum endpoint novo. Gates inalterados (Princípio XIII): `/orcamento/settings*` →
`_require_superadmin`; `/orcamento/calcular`, `/orcamento/opcoes` → `_require_vendas` (COMERCIAL ou
SUPERADMIN; FINANCEIRO 403).

## `POST /api/orcamento/calcular` — resposta ampliada

Entrada: inalterada (`event_date` já existe no payload, `"AAAA-MM-DD"` ou `""`).

Saída (`quote`): chave nova `data_especial`:

```json
{ "quote": { "...": "...", "markup_used": [3.34, 3.34, 3.34, 3.34],
             "data_especial": { "chave": "natal", "rotulo": "Véspera e Natal", "markup": [3.34, 3.34, 3.34, 3.34],
                                "nota_mensagem": "Valores especiais de 24 e 25 de dezembro." },
             "memoria": [ { "label": "Papai Noel", "detalhe": "cachê da data especial", "valores": [1000, 2000, 3000, 4000], "tipo": "cache" },
                          { "label": "× Markup", "detalhe": "Véspera e Natal · 24/12", "valores": [3.34, 3.34, 3.34, 3.34], "tipo": "markup" } ] },
  "snapshot": { "...": "...", "event_date": "2026-12-24" } }
```

Sem faixa: `"data_especial": null`, `markup_used` = markup normal, memória como hoje. Performer
elevado ao piso leva `"piso da data especial"` no `detalhe`. A `nota_mensagem` vai no quote porque o
PDF e o orçamento congelado não releem a tabela. A `message` ganha, na faixa, a linha
`\n\n_<nota_mensagem>_` logo após o bloco de investimento (junto da frase de deslocamento da 262).

## `GET /api/orcamento/opcoes` — já devolve o bloco

`settings.datas_especiais` chega inteiro (o endpoint devolve `_cfg.load()`); o React usa `dias` e
`rotulo`/`markup` para o aviso. Sem mudança de código no endpoint.

## `POST /api/orcamento/settings` — corpo ampliado

Corpo: o dict completo, agora com `datas_especiais` opcional:

```json
{ "datas_especiais": { "natal": { "rotulo": "Véspera e Natal", "dias": ["12-24", "12-25"],
    "markup": [3.34, 3.34, 3.34, 3.34],
    "cache": { "Papai Noel": [1000, 2000, 3000, 4000], "Ajudante do Noel": [650, 1300, 1950, 2600] },
    "coordenador": [500, 1000, 1500, 2000], "piso": [650, 1300, 1950, 2600],
    "nota_mensagem": "Valores especiais de 24 e 25 de dezembro." } } }
```

Validação no núcleo (`settings.validar_datas_especiais` → `SettingsValidationError`; o endpoint
devolve 400 no envelope `json_error`, `fields` com a chave `datas_especiais.<faixa>.<campo>`):

| Campo | Regra | Mensagem |
|---|---|---|
| bloco | dict | `datas_especiais` → "bloco inválido" |
| chave da faixa | `^[a-z0-9_]{1,30}$` e valor dict | `datas_especiais.<faixa>` → "faixa inválida" |
| `rotulo` | str 1–60 | "informe o rótulo" / "rótulo com mais de 60 caracteres" |
| `dias` | lista de `MM-DD` reais (29/02 aceito), sem repetição, sem dia que já esteja em outra faixa; **vazia = faixa desligada** | "informe os dias (DD/MM)" / "dia inválido: <MM-DD>" / "dia repetido: <DD/MM>" / "<DD/MM> já está na faixa <outra>" |
| `markup` | 4 números finitos em `[1.0, 6.0]`, gravados com 2 casas (HALF_UP) | "4 valores entre 1 e 6 (coeficiente)" |
| `cache` | dict; nomes existentes em `especiais`; 4 valores **> 0** (`parse_brl`; string inválida, zero, negativo ou infinito é erro, nunca default — a sobrescrita passa por fora do piso) | "sobrescritas inválidas" / "especial desconhecido: <nome>" / "4 valores em R$ maiores que zero (remova a sobrescrita para usar o piso)" |
| `coordenador`, `piso` | 4 valores ≥ 0 finitos (idem) | "4 valores em R$" |
| `nota_mensagem` | str ≤ 200; quebras de linha viram espaço | "nota com mais de 200 caracteres" |

Envelope: `json_error("Datas especiais inválidas.", 400, fields=...)`. Remover a chave `natal` do
bloco grava sem ela, mas a carga seguinte (`_migrar_307`) recria a faixa padrão: desligar é
`dias: []`.

Resposta: `{ "settings": <dict completo gravado> }` (como hoje). **O bloco enviado substitui o
salvo** (a tela manda o dict inteiro); chave `datas_especiais` ausente no corpo = mantém a salva.
Corpo inválido não grava nada. `DELETE /api/orcamento/settings/especiais/<nome>` passa a tirar a
sobrescrita do especial de todas as faixas.
