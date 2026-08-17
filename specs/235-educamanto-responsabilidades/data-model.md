# Data Model — Feature 235: EducaManto por responsabilidades

## EducaMantoMusical (tabela `educamanto_musicals`, rename de `educamanto_packages`)

| Campo | Tipo | Regra |
|---|---|---|
| id | int PK | preservado do pacote Master de origem |
| name | str(200) único | ex.: "Uma Aventura Animal" (sufixo " - Master" removido na migração) |
| num_personagens | int ≥ 0 | NOVO — ex.: 9 (declarado, aparece no PDF) |
| num_producao | int ≥ 0 | NOVO — ex.: 2 |
| num_ensaios | int ≥ 2, default 2 | NOVO — multiplica os custos de ensaio |
| margin_1s / margin_2s / margin_1s_days / margin_2s_days | float | mantidos (1.41 / 1.70 / 1.50 / 1.80 hoje) |
| discount_days | int | mantido (3 em produção; default do model alinhado para 3) |
| discount_pct | float | mantido (0.05) |
| ensemble_1s / _2s / _1s_days / _2s_days | float | mantidos (350 / 600 / 300 / 550) |
| ~~custo_som_* / custo_iluminacao_*~~ | — | 3ª rodada: viraram a tabela única por combinação em `pricing_config['educamanto_som_luz']` (não são colunas do musical) |
| ~~custo_cenario_*~~ | — | 4ª rodada: cenário saiu das responsabilidades (sem custo) — colunas removidas |
| custo_alimentacao_1s / _2s | float/pessoa | NOVO — migrado do item "Catering apresentação" (55 / 73) |
| created_at | datetime | mantido |

Removidos: `commission_rate` (campo morto — nunca usado em cálculo; UI enganava com "% s/ lucro").

## EducaMantoMusicalItem (tabela `educamanto_musical_items`, rename de `educamanto_items`)

Itens de custo sempre inclusos (elenco, produção, gráfica, caterings de ensaio…). Campos mantidos: `musical_id` (rename de package_id), `name`, `qty`, `cost_1s`, `cost_2s`, `cost_1s_days`, `cost_2s_days`, `sort_order`, `ensemble_add`.

Mudanças de conteúdo na migração:
- Item "Som" → vira `custo_som_*` do musical (item removido).
- Item "Catering apresentação" → vira `custo_alimentacao_*` (item removido; a qty era o headcount antigo, agora derivado).
- Item "Transporte" (R$ 600) → removido (substituído pela regra caminhão SP R$ 800 / vans fora de SP).
- Demais itens preservados como estão.

## Constantes globais (módulo único, provisórias até o dono enviar)

- `SONOPLASTA_1S/_2S/_1S_DAYS/_2S_DAYS` — sempre incluso.
- `TECNICO_SOM_*` — incluso quando som = Manto.
- `TECNICO_ILUMINACAO_*` — incluso quando iluminação = Manto.
- `SOM_AREA_FECHADA_M2` / `SOM_AREA_ABERTA_M2` — aviso do PDF.
- Config: `pricing_config['transporte']['caminhao_sp'] = 800` (nova chave, editável nas Configurações de Preços).

## Matriz de equipe técnica (derivada, não persistida)

| som | iluminação | técnicos | headcount extra |
|---|---|---|---|
| Manto | Manto | sonoplasta + téc. som + téc. iluminação | +3 |
| Manto | Contratante | sonoplasta + téc. som | +2 |
| Contratante | Manto | sonoplasta + téc. iluminação | +2 |
| Contratante | Contratante | sonoplasta | +1 |

`headcount = num_personagens + num_producao + técnicos do caso + ensemble` → cadeiras do camarim, itens por pessoa, adicional de viagem.

## EducaMantoQuote (tabela `educamanto_quotes` — inalterada estruturalmente)

Campos atuais mantidos (`user_id`, `client_name`, `packages_label`, `snapshot`, `created_at`). `packages_label` passa a listar "musical (resumo das responsabilidades)" por configuração.

### Snapshot v2 (JSON em `snapshot`)

```jsonc
{
  "version": 2,
  "client_name": "Colégio X",
  "event_date": "2026-09-12",
  "observacao": "texto livre do vendedor",
  "configs": [
    {
      "musical_id": 1,
      "musical_name": "Uma Aventura Animal",
      "d1": 1, "d2": 0, "ensemble": 2,
      "responsabilidades": {
        "som": "manto", "iluminacao": "contratante",
        "alimentacao": "manto", "cenario": "manto"
      },
      "fora_sp": false, "km_ida": null,
      "acrescimo": 500.0,
      "contratacao_manto": {            // opcional
        "inputs": { /* payload calculate_quote sem NF/fora_sp */ },
        "duracoes": ["1h", "2h"],
        "totais": {"1h": 3200.0, "2h": 4100.0}
      },
      "resultado": {                     // SEMPRE recalculado no servidor
        "headcount": 13,
        "tecnicos": ["sonoplasta", "tecnico_som"],
        "transporte_total": 800.0,
        "sem_nota": 15400.0, "com_nota": 18400.0,
        "a_vista_sem_nota": 14630.0, "a_vista_com_nota": 17480.0,
        "combinados": {"1h": {"sem": 18600.0, "com": 22200.0}}   // se contratação Manto
      }
    }
  ]
}
```

Snapshots **v1** (sem `version`): continuam sendo lidos pelo caminho atual (PDF antigo re-renderiza idêntico). "Recalcular" de v1: mapeia `package_id`→musical (por id preservado ou prefixo do nome), pré-marca responsabilidades pelo nível antigo (Econômica → alimentação/iluminação contratante; Intermediário → tudo Manto com aviso) e informa o vendedor.

## Migração (Alembic, uma revisão)

1. Rename das duas tabelas + rename `package_id` → `musical_id`.
2. Colunas novas (com defaults provisórios) + drop `commission_rate`.
3. Data: apagar linhas não-Master (ids 9, 10, 13, 14, 16, 17, 19, 20, 24, 25, 27, 28, 30, 31, 32) e seus itens; tirar " - Master" dos nomes; mover Som/Catering apresentação/Transporte para colunas/regra nova; popular `num_personagens`/`num_producao` (valores confirmados por musical: UAA 9+2, etc. — validar contra headcounts reais 11/10/9/7/9/10 na implementação); `num_ensaios = 2`.
4. Alinhar default do model `discount_days = 3` (paridade com produção).
5. Downgrade: recriar estrutura antiga (dados dos níveis apagados não retornam — aceito e documentado; backup do dump antes do deploy).
