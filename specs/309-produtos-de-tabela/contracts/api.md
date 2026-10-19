# Contratos — 309 Produtos de tabela

> Nenhum endpoint novo. Mudanças aditivas em quatro rotas existentes + o shape do item do teto + a CLI do
> script. RBAC inalterado (constituição XIII): `_require_vendas` (COMERCIAL, SUPERADMIN) em `/calcular`,
> `/salvar`, `/opcoes`; `_require_superadmin` em `/settings`.

## `POST /api/orcamento/calcular` (vendas)

Payload: tudo de hoje + `produtos?: [{chave: string}]` (lista; repetição permitida; ausente = conta de
hoje). Erros (envelope `json_error`, 400): `fields.produtos` = `'O produto "X" não está mais na tabela de
preços — remova-o ou peça ao superadmin para recriá-lo.'` (chave desconhecida ou produto removido);
produto `ativo: false` NÃO é erro (continua resolvendo).

Resposta: `{quote, snapshot}` como hoje, com `quote.produtos`, `quote.produtos_total`, `quote.avisos`,
linhas `tipo: "produto"` na `memoria`, labels das vagas em `team_lines`, bloco do produto em `message`;
`snapshot.produtos` e `snapshot.produtos_total` (ver `data-model.md` §4–5).

Regras de conta (fonte única `app/orcamento/produtos.py`):

```text
cache_totals (avulsos + coordenadores_da_formula) × markup → "= Após markup"
+ Σ preco_aplicado dos produtos                                → "= Após produtos"   (NOVO)
+ brinde, noturno (só avulsos + coordenadores da fórmula quando inclui_noturno), técnico ×1,5,
  maquiador ×1,5 (incremento dos avulsos sobre as makes do produto), transporte especial, fora de SP,
  acréscimos (% sobre o total com produto; valores_brl), NF ÷ 0,84                 (como hoje)
total_custom = (total_4h − produtos_total) ÷ 4 × h + produtos_total               (régua >4h)
personalizado valor_final → totals = digitado (linhas produto saem da memória)
personalizado multiplicador → totals = cache_base × mult + produtos_total
coordenadores_da_formula = max(coordenador_qty, coord_produtos) − coord_produtos
```

Avisos (`quote.avisos`, pt-BR, do servidor):

| Situação | Texto |
|---|---|
| "Papai Noel" avulso sem produto | `Para a Visita Mágica use o produto de tabela em vez do item "Papai Noel".` |
| produto sem preço para a faixa da data | `"<rótulo>" não tem preço de <rótulo da faixa>: preço ESTIMADO (cachês × 2,0 × markup 3,0). Confira antes de enviar.` |
| coordenador_qty elevado pelos produtos | `Coordenador: N incluído(s) no produto.` |

## `POST /api/orcamento/salvar` (vendas)

Grava `result` inteiro como hoje (`orcamento_write.py:57-70`); `form_snapshot.produtos` e
`result_snapshot.produtos` chegam prontos do `/calcular`. Nenhuma validação nova; o React só manda quando
`quote.produtos` veio na resposta (FR-017).

## `GET /api/orcamento/opcoes` (vendas) e `GET /api/orcamento/settings` (superadmin)

`settings` inteiro já migrado — inclui `produtos` (os dois padrão na primeira carga) e
`produtos_estimativa`. A calculadora lê `settings.produtos` (só `ativo`) para o Combobox e
`settings.datas_especiais[*].dias` para a dica (307). Registrado: os cachês "pela tabela" já chegam ao
navegador de todo comercial pela tabela inteira (não é regressão).

## `POST /api/orcamento/settings` (superadmin)

Aceita `produtos` e `produtos_estimativa` no corpo (`settings` inteiro, como o React manda); validação
no núcleo (`settings.validar_produtos(bloco, estimativa, especiais, datas_especiais)` →
`SettingsValidationError`; o endpoint devolve `json_error("Produtos de tabela inválidos.", 400,
fields=…)`). O bloco enviado SUBSTITUI o salvo; corpo inválido não grava nada; chave `produtos`
AUSENTE no corpo = mantém o salvo (um superadmin com a tela aberta desde antes do deploy não apaga os
produtos ao salvar outra coisa).

| Campo (`fields`) | Regra | Mensagem |
|---|---|---|
| `produtos` | dict | "bloco inválido" |
| `produtos.<chave>` | `^[a-z0-9_]{1,30}$` e dict | "produto inválido" |
| `.rotulo` | 1–60 | "informe o rótulo" / "rótulo com mais de 60 caracteres" |
| `.descricao` | ≤ 120 | "descrição com mais de 120 caracteres" |
| `.ativo` · `.inclui_noturno` | bool | "verdadeiro ou falso" |
| `.preco` | > 0 finito | "preço em R$ maior que zero" |
| `.por_faixa` | dict; chaves ∈ `datas_especiais` | "faixa desconhecida: <chave>" |
| `.por_faixa.<faixa>.preco` | > 0 finito | "preço em R$ maior que zero" |
| `.vagas` | lista 1–10 | "de 1 a 10 vagas" |
| `.vagas.<i>.label` | 1–120 | "informe o nome da vaga" / "nome com mais de 120 caracteres" |
| `.vagas.<i>.tipo` | ∈ especial, ator, coordenador, maquiador | "tipo de vaga desconhecido: <tipo>" |
| `.vagas.<i>.cache` | `null` ou > 0 finito | "cachê em R$ maior que zero, ou vazio para usar a tabela" |
| `produtos_estimativa.fator_cache` | > 0 finito | "fator maior que zero" |
| `produtos_estimativa.markup` | em [1, 6] | "markup entre 1 e 6 (coeficiente)" |

Label de vaga `especial` que não existe em `especiais` NÃO é erro de save (a vaga sai sem teto com nota);
o card avisa em amarelo.

## Item do teto — `_compute_performer_caches(snapshot, horas_extra, data_evento)` (interno)

Lê `snapshot["produtos"]` (ausente = hoje). Ordem: vagas `character` dos produtos → `performers` →
extras (coordenadores dos produtos → coordenadores da fórmula → Técnico → Maquiador do produto ou
genérico). Item de produto: mesmo shape + `origem: "produto"`, `produto_chave`; `cache_Nh` flat =
cachê resolvido (+ `transport_add` se fora de SP; sem `noturno_add` quando `inclui_noturno`);
`cache_custom` = o mesmo; produto removido → `cache_Nh: null` com nota. Consumidores inalterados:
prefill (`routes.py:3245-3275`), criação (`:3802-3816`, pareamento posicional `:3508-3523`,
`_create_extra_roles_from_orcamento :3562-3612`), vínculo 273 (`orcamento_evento_ops.py:658-751`, casa
por nome). `_build_orcamento_prefill` e `_total_da_duracao` passam a usar `produtos_total` na régua.

## `app/educamanto/quote_ops.py::_totais_contratacao` (interno)

`payload.pop("produtos", None)` ao lado de `event_date`/`nota_fiscal`/`fora_sp` (`:119-140`).

## CLI — `specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py`

(`scripts/oneoff/` é gitignored; o script mora na pasta da spec, como o da 239b.)

```bash
MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py            # relatório
MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py --execute  # corrige
```

Seleção: `EventRole` com `character_name` ∈ {"Papai Noel", "Ajudante do Noel"} e `cache_cap` exatamente
712,00 / 423,00 em eventos com `start_at >= 2026-10-16`. Relatório por linha: evento, data, vaga, teto,
cachê, artista, ação ("rebaixar para 600" | "não corrigida — cachê digitado" | "não corrigida — artista
escalado"). `--execute`: `cache_cap` → 600 / 270 e `cache_cap_note += " (teto corrigido pela 309: 712 →
600)"` só nas linhas "rebaixar"; um `commit` no fim; imprime o total corrigido e o restante. Saída UTF-8.
