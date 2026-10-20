# Data model — 309 Produtos de tabela

> Phase 1 do `/speckit-plan`, revisto pelo `/speckit-analyze` (19/10). Nenhuma tabela ou coluna nova
> (sem migration). Tudo mora no JSON `site_settings.pricing_config` (bloco `produtos` +
> `produtos_estimativa`), no `OrcamentoHistory.form_snapshot`/`result_snapshot` (chave `produtos`) e
> nas colunas já existentes de `EventRole` (`cache_cap`, `cache_cap_note`; `app/models.py:565-607`).

## 1. `pricing_config.produtos` (dict chave → produto)

```json
"produtos": {
  "visita_magica": {
    "rotulo": "Visita Mágica — Papai Noel",
    "descricao": "visita padrão (até 1h)",
    "ativo": true,
    "preco": 2500.0,
    "por_faixa": { "natal": { "preco": 5000.0 } },
    "vagas": [
      { "label": "Papai Noel",  "tipo": "especial",    "cache": null, "needs_makeup": true },
      { "label": "Coordenador", "tipo": "coordenador", "cache": null, "needs_makeup": false },
      { "label": "Maquiador",   "tipo": "maquiador",   "cache": null, "needs_makeup": false }
    ],
    "inclui_noturno": true
  },
  "visita_magica_ajudante": {
    "rotulo": "Visita Mágica — Papai Noel + Ajudante",
    "descricao": "visita padrão (até 1h)",
    "ativo": true,
    "preco": 3600.0,
    "por_faixa": { "natal": { "preco": 6500.0 } },
    "vagas": [
      { "label": "Papai Noel",       "tipo": "especial",    "cache": null, "needs_makeup": true },
      { "label": "Ajudante do Noel", "tipo": "especial",    "cache": null, "needs_makeup": false },
      { "label": "Coordenador",      "tipo": "coordenador", "cache": null, "needs_makeup": false },
      { "label": "Maquiador",        "tipo": "maquiador",   "cache": null, "needs_makeup": false }
    ],
    "inclui_noturno": true
  }
},
"produtos_estimativa": { "fator_cache": 2.0, "markup": 3.0 }
```

| Campo | Tipo | Regra (validação `settings.validar_produtos`; erro `produtos.<chave>.<campo>` / `produtos.<chave>.vagas.<i>.<campo>`) |
|---|---|---|
| chave | str | `^[a-z0-9_]{1,30}$` (`CHAVE_FAIXA_RE`) |
| `rotulo` | str | 1–60 caracteres |
| `descricao` | str | 0–120; vai à mensagem/PDF entre parênteses; vazia = nada |
| `ativo` | bool | `false` some do Combobox; continua resolvendo snapshots antigos |
| `preco` | float | > 0, finito, ≤ `_DINHEIRO_MAX`; `parse_brl`; 2 casas HALF_UP |
| `por_faixa` | dict | chave ∈ `datas_especiais` (do MESMO corpo, já validado); `{preco}` com as regras de `preco`; faixa inexistente é DESCARTADA com aviso (não 400); ausente/vazio = estimativa na data de faixa |
| `vagas` | list | 1–10 itens |
| `vagas[].label` | str | 1–120 (`EventRole.character_name` é String(120)); tipo `coordenador` força "Coordenador" e `maquiador` força "Maquiador" (o `_ensure_coordinator` e o vínculo 273 casam por esses nomes); é o nome da vaga e a chave do casamento por nome no vínculo 273 |
| `vagas[].tipo` | str | ∈ `TIPOS_DE_VAGA = {"especial", "ator", "coordenador", "maquiador"}` |
| `vagas[].cache` | float \| null | `null` = pela tabela vigente na data (coluna 1h); número > 0 finito fixa |
| `vagas[].needs_makeup` | bool | só para `especial`/`ator` (coordenador/maquiador forçados a `false`); padrão `false`; conta como make COMUM no Maquiador e marca a vaga no vínculo 273 |
| `inclui_noturno` | bool | padrão `true`: produto não soma noturno (venda e teto); `false`: +50 por vaga especial/ator/coordenador |
| `produtos_estimativa.fator_cache` | float | > 0 finito; padrão 2,0 |
| `produtos_estimativa.markup` | float | em [1, 6]; padrão 3,0 |

**Normalização na carga (`_migrar_309`, dentro do `try` de `load()`)**: `setdefault("produtos",
deepcopy(DEFAULTS["produtos"]))` e `setdefault("produtos_estimativa", …)` quando a chave está AUSENTE
ou o bloco NÃO é um dicionário (`null`, lista, texto); com um dicionário (mesmo vazio), cada produto é
normalizado na defensiva (`isinstance` em tudo; produto
sem `rotulo`/`preco` válido ou sem `vagas` é DESCARTADO; vaga malformada é descartada; `por_faixa` com
faixa inexistente é descartada; labels de coordenador/maquiador forçados) — nunca preço 0, nunca
exceção. Também aqui: `especiais["Papai Noel"] == [712, 800, 850, 900]` → `[600, 650, 675, 700]` e
`"Ajudante do Noel" == [423, 480, 510, 540]` → `[270, 320, 345, 370]` (inversa guardada); `_migrar_307`
deixa de trocar 600→712 e seus comentários são reescritos.

**Resolução do cachê `null` (`produtos.cache_da_vaga(vaga, faixa, cfg)`)** — sempre coluna 1h,
`has_show = False`, replicada nas 4 colunas (flat):

| `tipo` | Fonte | Normal | Faixa natal (307) |
|---|---|---|---|
| especial | `label in cfg["especiais"]` → `get_especial_prices(label, show=False, faixa=)` + `cache_na_faixa`; senão **`None`** | Noel 600 · Ajudante 270 | 1.000 · 650 |
| coordenador | `get_coordenador_prices(False, 1, faixa)` | 250 | 500 |
| maquiador | `calcular_maquiador(1, 0)` (`make_1`) — a vaga única do orçamento usa `calcular_maquiador(Σ makes dos produtos + comuns avulsos, especiais avulsos)` | 250 | 250 |
| ator | `get_ator_prices("cara_limpa", False, False)` + `cache_na_faixa` (piso) | 200 | 650 (piso) |

Label de `especial` que não existe em `especiais` → vaga **sem teto** (`None`) com nota — nunca 0 nem
piso (a checagem vem ANTES do getter, que devolveria zeros).

## 2. Preço do produto (`produtos.preco_do_produto`)

```text
faixa is None                      → preco_aplicado = preco;                 faixa_chave = None;   estimado = False
faixa e faixa.chave ∈ por_faixa    → preco_aplicado = por_faixa[chave].preco; faixa_chave = chave; estimado = False
faixa e faixa.chave ∉ por_faixa    → preco_aplicado = Q(Σ cache_1h NORMAL das vagas com cachê × fator_cache × markup);
                                     faixa_chave = chave; estimado = True   (Q = Decimal HALF_UP, 2 casas)
```

Visita Mágica — Papai Noel sem preço de natal em 24/12: (600 + 250 + 250) × 2,0 × 3,0 = **6.600,00**.
Vagas sem cachê resolvível ficam fora da soma e geram aviso. Texto do aviso com os fatores vigentes:
`"<rótulo>" não tem preço de <faixa>: preço ESTIMADO (cachês × {fator_cache} × markup {markup}). Confira
antes de enviar.`

## 3. Payload de `/calcular` e `/salvar`

```json
"produtos": [ { "chave": "visita_magica" }, { "chave": "visita_magica" } ]
```

Lista (repetição permitida); ausente/vazia = conta de hoje. Chave desconhecida ou produto removido →
`QuoteValidationError("produtos", 'O produto "X" não está mais na tabela de preços — remova-o ou peça
ao superadmin para recriá-lo.')`.

## 4. `quote` (resposta e `result_snapshot`) — chaves novas SEMPRE presentes

```json
"produtos": [
  { "chave": "visita_magica", "rotulo": "Visita Mágica — Papai Noel", "descricao": "visita padrão (até 1h)",
    "preco_aplicado": 5000.0, "faixa_chave": "natal", "estimado": false,
    "vagas": ["Papai Noel", "Coordenador", "Maquiador"] }
],
"produtos_total": 5000.0,
"coordenadores_inclusos": 1,
"avisos": [ "Para a Visita Mágica use o produto de tabela em vez do item \"Papai Noel\"." ]
```

- Sem produto: `produtos: []`, `produtos_total: 0.0`, `coordenadores_inclusos: 0`, `avisos: []` —
  a presença da chave é o que distingue backend novo de backend velho na janela de deploy (FR-017).
  Quote antigo (salvo antes da feature) não tem as chaves: o React lê com `?? []`/`?? 0`.
- `avisos` é lista de strings pt-BR do servidor (a tela nunca decide); vazia quando nada a dizer.
- `memoria` ganha linhas `tipo: "produto"` (uma por exemplar; `label` = rótulo, `detalhe` = "preço de
  tabela" | "preço de tabela · Véspera e Natal" | "preço estimado (sem preço de Véspera e Natal)";
  `valores` iguais nas 4 colunas) e a subtotal "= Após produtos". Invariante: `Σcache × markup +
  Σproduto + Σpos = TOTAL` (multiplicador: `Σcache × mult + Σproduto = TOTAL`; valor final: só a linha
  digitada).
- `team_lines` ganha os labels das vagas `especial`/`ator` do produto (ordem: produto → avulsos).
- `message`: com só produto (sem avulsos e sem coordenador da fórmula) UM bloco "Visita Mágica —
  Papai Noel (visita padrão (até 1h)): R$ 2.500,00" e PIX único (`show_1h` true, demais false,
  `total_custom` None); com avulsos, o bloco do produto antes dos blocos de duração; "(estimativa)"
  quando `estimado`.

## 5. `snapshot` (`form_snapshot`) — preço E composição congelados

```json
"produtos": [
  { "chave": "visita_magica", "rotulo": "Visita Mágica — Papai Noel", "preco_aplicado": 2500.0,
    "faixa_chave": null, "estimado": false,
    "vagas": [ { "label": "Papai Noel", "tipo": "especial", "cache": null, "needs_makeup": true },
               { "label": "Coordenador", "tipo": "coordenador", "cache": null, "needs_makeup": false },
               { "label": "Maquiador", "tipo": "maquiador", "cache": null, "needs_makeup": false } ] }
],
"produtos_total": 2500.0
```

Congela o preço vendido E as vagas: o teto (prefill, criação, vínculo 273) emite as vagas a partir
daqui — a tabela viva na data do evento dá só o VALOR do cachê (`cache: null`) — e por isso o
pareamento posicional da criação não depende de edições do produto entre o prefill e o Criar, e
produto apagado continua produzindo as vagas (com teto `None`). `produtos_total` alimenta a régua
(`total_na_duracao`) no prefill e em `_total_da_duracao`. Snapshot sem a chave → `produtos_total = 0`
e conta de hoje.

## 6. Régua >4h (`produtos.total_na_duracao`)

```text
total_na_duracao(total_4h, produtos_total, horas, acrescimos, nota_fiscal):     # total FINAL de 4h
    fixo  = produtos_total × (1 + Σ%/100) ÷ (0,84 se nota_fiscal)                 # o produto como está dentro do total
    return Q((total_4h − fixo) ÷ 4 × horas + fixo)                                # o resto escala (fixos inclusos)

base_na_duracao(base_4h, produtos_total, horas) = (base_4h − produtos_total) ÷ 4 × horas + produtos_total
```

Entrada = `totals[3]` na venda, `entry.total_4h` no prefill e em `_total_da_duracao` (mesma função, mesmo
float). Os acréscimos FIXOS escalam `÷ 4 × h` como a régua de sempre (sem produto a conta reproduz
exatamente `total_4h ÷ 4 × h`). As linhas de acréscimo do evento acima de 4h (305,
`acrescimos_do_orcamento`) são refeitas linha a linha por `_linhas_na_duracao`: base de 4h pela conta
inversa (`(líquido − fixos) ÷ (1 + Σ%)`), `base_h = base_na_duracao(base_4h, produtos_total, h)`, linha %
= `base_h × %`, fixa = `valor × h ÷ 4` — Σ linhas + base_h (÷ 0,84 com nota) = `total_na_duracao`. Um
fator único `total_h ÷ total_4h` (a 1ª versão) errava a fixa para baixo e a % para cima. Personalizado:
multiplicador → `total_na_duracao` sem acréscimos e sem NF (nada disso entrou no total); valor final →
`produtos_total = 0` no quote/snapshot, régua linear.

## 7. Item do teto (`_compute_performer_caches` → `caches[]`)

Mesmo shape de hoje (`routes.py:2974-3011`), com dois campos novos opcionais:

```json
{ "label": "Papai Noel", "role_type": "character", "needs_makeup": true, "is_singer": false,
  "cache_1h": 600, "cache_2h": 600, "cache_3h": 600, "cache_4h": 600, "cache_custom": 600,
  "cap_notes": { "cache_1h": "Papai Noel (cachê da tabela · produto Visita Mágica — Papai Noel): base 1h R$ 600,00 — teto R$ 600,00", "…": "…" },
  "origem": "produto", "produto_chave": "visita_magica" }
```

- `MARCA_PRODUTO = "cachê da tabela · produto"` (constante em `produtos.py`; a nota é
  `_montar_cap_note(f"{label} ({MARCA_PRODUTO} {rótulo})", "base 1h", valor, adicionais, total)`).
- Flat: `cache_Nh` iguais; `cache_custom` = o mesmo valor (não escala); sem `noturno_add` quando
  `inclui_noturno`; `transport_add` (fora de SP) soma como nas demais.
- Produto removido ou label de especial desconhecido: `cache_Nh = null`, `cap_notes` com "produto X
  não está mais na tabela — teto não aplicado" (visível só no prefill; `EventRole` nasce sem teto e
  sem nota, como hoje para cap `None`).
- Ordem de emissão: vagas `character` dos produtos (das vagas congeladas) → `performers` → extras
  (coordenadores dos produtos → coordenadores da fórmula → Técnico → UM Maquiador por orçamento com
  `calcular_maquiador(Σ makes dos produtos + comuns avulsos, especiais avulsos)`).

## 8. `EventRole` (sem mudança de schema)

`cache_cap` = cachê resolvido do produto; `cache_cap_note` = nota acima; `cache_value` nasce vazio;
`character_name` = `label` da vaga. Script 309: seleção `cache_cap ∈ {712.00, 423.00}` em eventos com
`start_at ≥ 2026-10-16` (qualquer nome, para o relatório); correção só em "Papai Noel"/"Ajudante do
Noel" com `cache_value IS NULL AND talent_id IS NULL`: 712 → 600 / 423 → 270 e `cache_cap_note += "
(teto corrigido pela 309: {antes} → {depois})"`.

## 9. Tipos TypeScript (`frontend/apps/internal/src/lib/orcamento.ts`)

```ts
export interface VagaDoProduto { label: string; tipo: "especial" | "ator" | "coordenador" | "maquiador"; cache: number | null; needs_makeup: boolean }
export interface ProdutoDeTabela { rotulo: string; descricao: string; ativo: boolean; preco: number;
  por_faixa: Record<string, { preco: number }>; vagas: VagaDoProduto[]; inclui_noturno: boolean }
export interface ProdutosEstimativa { fator_cache: number; markup: number }
export interface ProdutoAplicado { chave: string; rotulo: string; descricao: string; preco_aplicado: number;
  faixa_chave: string | null; estimado: boolean; vagas: string[] }
// PricingSettings.produtos?: Record<string, ProdutoDeTabela>; PricingSettings.produtos_estimativa?: ProdutosEstimativa
// CalcularOrcamentoInput.produtos?: { chave: string }[]
// Quote.produtos?: ProdutoAplicado[]; Quote.produtos_total?: number; Quote.coordenadores_inclusos?: number; Quote.avisos?: string[]
// MemoriaLinha.tipo: "cache" | "subtotal" | "markup" | "pos" | "total" | "produto"   (linha :173 — a união real não tem "info")
// OrcamentoFormSnapshot.produtos?: { chave: string; rotulo: string; preco_aplicado: number; faixa_chave: string | null; estimado: boolean; vagas: VagaDoProduto[] }[]
```
