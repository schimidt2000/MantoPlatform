# Contratos — 309 Produtos de tabela

> Nenhum endpoint novo. Mudanças aditivas em CINCO rotas existentes + o shape do item do teto + a CLI do
> script. RBAC inalterado (constituição XIII): `_require_vendas` (COMERCIAL, SUPERADMIN) em `/calcular`,
> `/salvar`, `/opcoes`; `_require_superadmin` em `GET` e `POST /settings`. Revisto pelo `/speckit-analyze`.

## `POST /api/orcamento/calcular` (vendas)

Payload: tudo de hoje + `produtos?: [{chave: string}]` (lista; repetição permitida; ausente = conta de
hoje). Erros (envelope `json_error`, 400): `fields.produtos` = `'O produto "X" não está mais na tabela de
preços — remova-o ou peça ao superadmin para recriá-lo.'` (chave desconhecida ou produto removido);
produto `ativo: false` NÃO é erro (continua resolvendo).

Resposta: `{quote, snapshot}` como hoje, com as chaves novas SEMPRE presentes em `quote`
(`produtos`, `produtos_total`, `coordenadores_inclusos`, `avisos` — vazias/zero sem produto), linhas
`tipo: "produto"` + "= Após produtos" na `memoria`, labels das vagas em `team_lines`, bloco do produto
em `message`; `snapshot.produtos` (preço e vagas congelados) e `snapshot.produtos_total` (ver
`data-model.md` §4–5).

Regras de conta (fonte única `app/orcamento/produtos.py`):

```text
total, da_formula, inclusos = split_coordenadores(coordenador_qty, min_coordenadores_avulsos, produtos)
cache_totals (avulsos + da_formula coordenadores) × markup       → "= Após markup"
+ produtos_total                                                 → "= Após produtos"   (NOVO)
+ brinde, noturno (avulsos + da_formula; vagas do produto só com inclui_noturno=false), técnico ×1,5,
  maquiador ×1,5 = incremento_make(mp, ra, ea) = calcular_maquiador(mp + ra, ea) − calcular_maquiador(mp, 0),
  transporte especial, fora de SP (num_going inclui as pessoas do produto), acréscimos (% sobre o total
  com produto; valores_brl), NF ÷ 0,84                           (como hoje)
total_custom = total_na_duracao(subtotal_4h_pre, produtos_total, h, acrescimos, nota_fiscal)   (régua >4h)
personalizado valor_final → totals = digitado (linhas produto e "= Após produtos" saem da memória)
personalizado multiplicador → totals = cache_base × mult + produtos_total (validação olha cache_base × mult)
só produto (sem avulsos e da_formula == 0) → show = [True, False, False, False], total_custom = None
```

Avisos (`quote.avisos`, pt-BR, do servidor; "N incluído(s) no produto" NÃO é aviso — vem em
`quote.coordenadores_inclusos`):

| Situação | Texto |
|---|---|
| "Papai Noel" avulso sem produto | `Para a Visita Mágica use o produto de tabela em vez do item "Papai Noel".` |
| produto sem preço para a faixa da data | `"<rótulo>" não tem preço de <rótulo da faixa>: preço ESTIMADO (cachês × {fator_cache} × markup {markup}). Confira antes de enviar.` |
| vaga do produto sem cachê resolvível (label fora da tabela) | `"<label>" não está na tabela de preços: a vaga nasce sem teto e ficou fora da estimativa.` |

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

Aceita `produtos` e `produtos_estimativa` no corpo (`settings` inteiro, como o React manda). Ordem: o
ramo `produtos` roda DEPOIS do ramo `datas_especiais` e valida `por_faixa` contra `s["datas_especiais"]`
já atualizado. Validação no núcleo (`settings.validar_produtos(bloco, estimativa, especiais,
datas_especiais) → (produtos_limpos, estimativa_limpa, avisos)` → `SettingsValidationError`; o endpoint
devolve `json_error("Produtos de tabela inválidos.", 400, fields=…)`; `avisos` (faixa órfã descartada)
voltam na resposta 200 em `avisos`). O bloco enviado SUBSTITUI o salvo; corpo inválido não grava nada;
chave `produtos` AUSENTE no corpo = mantém o salvo (um superadmin com a tela aberta desde antes do
deploy não apaga os produtos ao salvar outra coisa).

| Campo (`fields`) | Regra | Mensagem |
|---|---|---|
| `produtos` | dict | "bloco inválido" |
| `produtos.<chave>` | `^[a-z0-9_]{1,30}$` e dict | "produto inválido" |
| `.rotulo` | 1–60 | "informe o rótulo" / "rótulo com mais de 60 caracteres" |
| `.descricao` | ≤ 120 | "descrição com mais de 120 caracteres" |
| `.ativo` · `.inclui_noturno` | bool | "verdadeiro ou falso" |
| `.preco` | > 0 finito | "preço em R$ maior que zero" |
| `.por_faixa` | dict; faixa inexistente é descartada com aviso (não erro) | — |
| `.por_faixa.<faixa>.preco` | > 0 finito | "preço em R$ maior que zero" |
| `.vagas` | lista 1–10 | "de 1 a 10 vagas" |
| `.vagas.<i>.label` | 1–120; coordenador → "Coordenador", maquiador → "Maquiador" (forçados) | "informe o nome da vaga" / "nome com mais de 120 caracteres" |
| `.vagas.<i>.tipo` | ∈ especial, ator, coordenador, maquiador | "tipo de vaga desconhecido: <tipo>" |
| `.vagas.<i>.cache` | `null` ou > 0 finito | "cachê em R$ maior que zero, ou vazio para usar a tabela" |
| `.vagas.<i>.needs_makeup` | bool (só especial/ator; demais forçados a false) | "verdadeiro ou falso" |
| `produtos_estimativa.fator_cache` | > 0 finito | "fator maior que zero" |
| `produtos_estimativa.markup` | em [1, 6] | "markup entre 1 e 6 (coeficiente)" |

Label de vaga `especial` que não existe em `especiais` NÃO é erro de save (a vaga sai sem teto com nota);
o card avisa em amarelo.

## Item do teto — `_compute_performer_caches(snapshot, horas_extra, data_evento)` (interno)

Lê `snapshot["produtos"]` (ausente = hoje) e emite as vagas a partir das vagas CONGELADAS de cada
exemplar. Ordem: vagas `character` dos produtos → `performers` → extras (coordenadores dos produtos →
coordenadores da fórmula → Técnico → UM Maquiador por orçamento). Item de produto: mesmo shape +
`origem: "produto"`, `produto_chave`; `cache_Nh` flat = cachê resolvido na data do evento com
`has_show=False` (+ `transport_add` se fora de SP; sem `noturno_add` quando `inclui_noturno`);
`cache_custom` = o mesmo; produto removido ou label de especial desconhecido → `cache_Nh: null` com nota
(só prefill). `cap_notes` com `MARCA_PRODUTO`. Consumidores inalterados: prefill (`routes.py:3245-3275`),
criação (`:3802-3816`, pareamento posicional `:3508-3523`, `_create_extra_roles_from_orcamento
:3562-3612`), vínculo 273 (`orcamento_evento_ops.py:658-751`, casa por nome). `_build_orcamento_prefill`,
`_total_da_duracao` e `acrescimos_do_orcamento` (duração custom) passam a usar `total_na_duracao` com o
snapshot (`snapshot_do_orcamento(entry)`).

## `resumo_do_orcamento` (interno, aba Comercial do evento)

Inclui os labels das vagas `especial`/`ator` dos produtos em `personagens` e as makes dos produtos em
`maquiagens` (FR-009).

## `app/educamanto/quote_ops.py::_totais_contratacao` (interno)

`payload.pop("produtos", None)` ao lado de `event_date`/`nota_fiscal`/`fora_sp` (`:119-140`); o
`inputs` do snapshot do EducaManto pode guardar a chave — ignorada em todo recálculo.

## CLI — `specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py`

(`scripts/oneoff/` é gitignored; o script mora na pasta da spec, como o da 239b.)

```bash
MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py            # relatório
MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py --execute  # corrige
```

Seleção (relatório): `EventRole` com `cache_cap` exatamente 712,00 ou 423,00 em eventos com `start_at >=
2026-10-16`, qualquer nome. Correção (`--execute`): só `character_name` ∈ {"Papai Noel", "Ajudante do
Noel"} com `cache_value IS NULL AND talent_id IS NULL` → `cache_cap` 600 / 270 e `cache_cap_note += "
(teto corrigido pela 309: {antes} → {depois})"`; nome diferente, cachê digitado ou artista escalado →
"não corrigida — conferir à mão". Relatório por linha: evento, data, vaga, teto, cachê, artista, ação;
um `commit` no fim; imprime o total corrigido e o restante. Saída UTF-8; `MANTO_SEM_THREADS=1`.
