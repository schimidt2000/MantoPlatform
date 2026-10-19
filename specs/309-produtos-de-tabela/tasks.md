---
description: "Tasks da feature 309 — Produtos de tabela (Visita Mágica pelo preço da tabela de venda)"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Produtos de tabela — a Visita Mágica vendida pelo preço da tabela de venda

**Input**: artefatos em `/specs/309-produtos-de-tabela/` (worktree `C:\tmp\mp309`, branch
`309-produtos-de-tabela`; a árvore principal está com a 308 de outro chat — nada é escrito lá).
Revisto pelo `/speckit-analyze` em 19/10 (régua por `total_na_duracao`, vagas congeladas no snapshot,
um Maquiador por orçamento, `has_show=False` nas vagas do produto, helpers puros em `produtos.py`).

**Pré-requisitos**: plan.md, spec.md (7 histórias e a tabela "Verificação"), research.md (D1–D22),
data-model.md, contracts/api.md, quickstart.md

**Verificação (OBRIGATÓRIA neste projeto — constituição, Princípio VIII)**: `verify_309.py` é escrito na
fase Foundational, ANTES do núcleo, rodado VERMELHO (saída em `verify_309_primeira_falha.txt`; a
primeira rodada também grava o gabarito `verify_309_golden.json` no HEAD `6356b80`) e passa história a
história. Não existe pytest nem `tests/`.

**Organização**: por história da spec. Ordem pedida: verify → settings → `produtos.py` → quote_ops →
pdf → endpoint → EducaManto → teto → script → tipos TS + telas → conferência → `verify_307` + regressão
→ docs → converge. Sem migration. Commits por caminho: `feat(309): núcleo` · `feat(309): teto e
script` · `feat(309): telas` · `docs(309): …` — nunca `git add -A`.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: história a que a tarefa pertence (US1…US7)
- Caminho exato do arquivo na descrição

## Caminhos (Manto)

- Backend: `app/orcamento/{settings,produtos,quote_ops,pricing,pdf}.py` · `app/api/orcamento_write.py` ·
  `app/educamanto/quote_ops.py` · `app/calendar/{routes,orcamento_evento_ops}.py`
- Frontend: `frontend/apps/internal/src/{lib/orcamento.ts, components/MemoriaDeCalculo.tsx,
  components/orcamento/, pages/}`
- Verificação e script: `specs/309-produtos-de-tabela/{verify_309.py, verify_309_golden.json,
  rebaixar_tetos_noel_309.py}`; regressão `specs/307-…/verify_307.py` (encadeia `specs/305-…/verify_305.py`)

## Phase 1: Setup

- [ ] T001 Conferir o estado de partida e registrar em `specs/309-produtos-de-tabela/research.md` (seção
      "Estado de partida"): no `manto_local`, `pricing_config` cru (especiais Papai Noel/Ajudante, há
      `produtos`?), markup receptivo 1h, coordenador 1h (false/true), `maquiador.make_1`/`make_especial`,
      faixa `natal`; `git log -1` do worktree; junções de `node_modules` no worktree funcionando
      (`cd frontend && npm run typecheck` roda) — tudo só leitura

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [ ] T002 **`specs/309-produtos-de-tabela/verify_309.py`** — os 20 cenários da tabela "Verificação" da
      spec, no molde de `verify_307.py` + dublês do Google de `verify_305.py`: config real salva/restaurada
      por conexão separada; config de teste determinística (markup 2,6/2,5/2,45/2,4, coordenador
      250/300/325/350 e 300/350/375/400, `make_1` 250, `make_especial` 300, especiais Papai Noel
      `[712, 800, 850, 900]` e Ajudante `[423, 480, 510, 540]` GRAVADOS para provar a inversa, SEM
      `produtos` para provar os padrões, faixa `natal` da 307); usuários descartáveis `__v309_` sa / com /
      casting (login só por `POST /api/auth/login`); evento descartável só por `POST /api/events` com
      `cal_routes.insert_event` dublê, roles criadas/apagadas na mesma rodada; **cenário 1 = gabarito**
      (`verify_309_golden.json`: se ausente, grava quote + `message` + texto do PDF dos payloads sem
      produto/Noel/Ajudante — boneco + coordenador em 20/12 e 24/12, fora de SP, NF, BV — e sai como
      "GABARITO GRAVADO"; se presente, compara chave a chave ignorando só `produtos`, `produtos_total`,
      `coordenadores_inclusos`, `avisos`); cenário 2 afirma a invariante `Σcache × markup + Σproduto +
      Σpos == TOTAL` e o bloco único na mensagem/PDF; cenário 5 com dois produtos (UM Maquiador 300),
      avulso com show (coordenador do produto 250) e avulso de make especial; cenário 7 com NF e BV na
      régua 6h comparando venda × prefill × `_total_da_duracao`; cenário 8 afirma `MARCA_PRODUTO` e label
      desconhecido → `None`; cenário 13 com 7 corpos inválidos + faixa órfã → aviso; cenário 17 DEVE
      FALHAR (COMERCIAL 403); cenário 18 inclui vaga 712 de nome diferente ("conferir à mão"); cenário 19
      (`--regressao`) roda SÓ `verify_307.py --regressao` em subprocesso (ele encadeia a 305); cenário 20
      limpa e confere a restauração; `--so=…`
- [ ] T003 Rodar o verify ANTES do núcleo (grava o gabarito do cenário 1 no HEAD `6356b80`) e guardar a
      saída em `specs/309-produtos-de-tabela/verify_309_primeira_falha.txt` — esperado: 2–15 e 18 FALHAM
      pelos motivos certos (chave `produtos` ignorada → 2.210; sem `quote.produtos`; carga ainda entrega
      712; script inexistente), 1 (gabarito gravado) e 17 passam; commitar o gabarito
- [ ] T004 `app/orcamento/settings.py`: DEFAULTS — `especiais["Papai Noel"] = [600, 650, 675, 700]`,
      `especiais["Ajudante do Noel"] = [270, 320, 345, 370]`; bloco `produtos` com os dois padrão
      (`visita_magica`, `visita_magica_ajudante` conforme `data-model.md` §1, Noel com `needs_makeup`) e
      `produtos_estimativa = {"fator_cache": 2.0, "markup": 3.0}`; constantes `TIPOS_DE_VAGA`,
      `LABEL_FIXO_POR_TIPO = {"coordenador": "Coordenador", "maquiador": "Maquiador"}`,
      `PRODUTO_ROTULO_MAX = 60`, `PRODUTO_DESCRICAO_MAX = 120`, `PRODUTO_VAGAS_MAX = 10`, `NOEL_712 =
      [712, 800, 850, 900]`, `AJUDANTE_423 = [423, 480, 510, 540]`; apagar `PAPAI_NOEL_CACHE_ANTIGO` e o
      bloco de troca 600→712 de `_migrar_307`; REESCREVER os comentários que justificavam 712 (:16-18,
      :93-96) e acrescentar em :39-44 que a Visita Mágica agora é produto (`produtos`)
- [ ] T005 `app/orcamento/settings.py`: `_migrar_309(data)` — `setdefault` de `produtos` e
      `produtos_estimativa` só com chave AUSENTE; `_normalizar_produto` defensivo (descarta produto/vaga
      malformados e `por_faixa` de faixa inexistente; força labels por tipo; `needs_makeup` só
      especial/ator; nunca preço 0; `isinstance` em tudo); troca inversa guardada (`== NOEL_712` → 600…,
      `== AJUDANTE_423` → 270…); chamado por `_migrate` depois de `_migrar_307`; docstring: roda dentro do
      `try` de `load()`
- [ ] T006 `app/orcamento/settings.py`: `validar_produtos(bloco, estimativa, especiais, datas_especiais)
      -> tuple[dict, dict, list[str]]` (produtos limpos, estimativa limpa, avisos) levantando
      `SettingsValidationError` com `fields` `produtos.<chave>.<campo>` / `produtos.<chave>.vagas.<i>.<campo>`
      / `produtos_estimativa.<campo>` (regras e mensagens da tabela de `contracts/api.md`; labels de
      coordenador/maquiador forçados; `needs_makeup` bool só especial/ator; `por_faixa` de faixa
      inexistente DESCARTADA com aviso, não erro); label de especial desconhecido NÃO é erro
- [ ] T007 `app/orcamento/produtos.py` (NOVO, puro, docstring do porquê, type hints, constantes
      `MARCA_PRODUTO = "cachê da tabela · produto"`, textos dos avisos como templates):
      `resolver_produtos(selecao, cfg, faixa) -> list[ProdutoResolvido]` (chave desconhecida →
      `ProdutoDesconhecido(chave)`; aceita também a forma congelada do snapshot — com `vagas` — para o
      teto); `preco_do_produto(produto, faixa, cfg, estimativa) -> (preco, faixa_chave, estimado, avisos)`
      (Decimal HALF_UP; vagas sem cachê fora da soma); `cache_da_vaga(vaga, faixa, cfg) -> float | None`
      (`has_show=False`; `label in cfg["especiais"]` ANTES do getter, senão `None`); `split_coordenadores
      (coordenador_qty, min_coordenadores, produtos) -> (total, da_formula, inclusos)`;
      `makes_dos_produtos(produtos) -> int`; `incremento_make(mp, ra, ea) -> float`; `somar_produtos
      (produtos) -> float`; `total_na_duracao(subtotal_4h_pre, produtos_total, horas, acrescimos,
      nota_fiscal) -> float` (data-model §6); `subtotal_pre_acrescimos(total_4h, acrescimos, nota_fiscal)
      -> float` (conta inversa, molde `_conta_inversa`); `linhas_da_memoria(produtos) -> list[dict]`;
      `itens_do_teto(produtos, faixa, cfg, transport_add, noturno_add) -> list[dict]` (vagas `character`
      flat, `origem: "produto"`, notas com `MARCA_PRODUTO`, cache `None` com nota quando desconhecido);
      `coordenadores_do_teto(...)` e `makes_para_maquiador(produtos, performers)`; `vagas_congeladas
      (produto) -> list[dict]`; `avisos_para(performers, produtos) -> list[str]`

**Checkpoint**: verify vermelho pelos motivos certos e gabarito gravado; tabela com os padrões e a
inversa; fonte única pronta e sem consumidor.

---

## Phase 3: História 1 — A vendedora vende a Visita Mágica pelo preço da tabela (P1) 🎯 MVP

**Objetivo**: produto selecionado → 2.500 / 3.600 (5.000 / 6.500 em 24/25) iguais nas quatro colunas;
memória, mensagem e PDF com a linha do produto (bloco único quando só produto);
`quote.produtos`/`snapshot.produtos` com vagas congeladas.

**Verificação da história (obrigatória)**: cenários 2, 3, 4 e 12 (parte do avulso) em PASS; tela
`/orcamento` e `/orcamento/:id` abertas.

- [ ] T008 [US1] `app/orcamento/quote_ops.py` — `calculate_quote` só por chamadas a `produtos.py`: ler
      `payload.get("produtos")`, `produtos = resolver_produtos(...)` com `cfg_precos`/`faixa` já
      carregados (erro → `QuoteValidationError("produtos", …)`); `total, da_formula, inclusos =
      split_coordenadores(...)` substituindo `coordenador_qty` nos usos de venda (coordenador da fórmula,
      noturno `len(performers) + da_formula` (+ vagas do produto só com `inclui_noturno=false`),
      `num_going`); depois de "= Após markup": `totals[i] += produtos_total`, `linhas_da_memoria`, subtotal
      "= Após produtos"; maquiador = `incremento_make(...)` × 1,5; `team_lines` com os labels
      `especial`/`ator` do produto; `so_produto = produtos and not performers and da_formula == 0` →
      `show = [True, False, False, False]`, `total_custom = None`; `quote["produtos"]`,
      `quote["produtos_total"]`, `quote["coordenadores_inclusos"]`, `quote["avisos"]` SEMPRE emitidos;
      `snapshot["produtos"]` (`{chave, rotulo, preco_aplicado, faixa_chave, estimado, vagas}`) e
      `snapshot["produtos_total"]`; régua `total_custom = total_na_duracao(subtotal_4h_pre, …)` com o
      subtotal de 4h capturado antes dos acréscimos; personalizado: `valor_final` filtra `produto` e a
      subtotal; `multiplicador` → `totals = cache_base × mult + produtos_total` (validação sobre
      `cache_base × mult`)
- [ ] T009 [US1] `app/orcamento/quote_ops.py` — mensagem WhatsApp: bloco do produto ("Visita Mágica —
      Papai Noel (visita padrão (até 1h)): R$ 2.500,00"; "(estimativa)" quando `estimado`) antes dos
      blocos de duração; com `so_produto` só o bloco do produto e um PIX; `_rotulo_da_faixa` reusado
- [ ] T010 [P] [US1] `app/orcamento/pdf.py`: linha do produto (rótulo, descrição, preço aplicado,
      "(estimativa)") logo abaixo da lista da equipe, antes de "Investimento"; com `show_1h` só, uma
      `_price_row` e um PIX; lê `quote.get("produtos") or []` (legado sem a chave)
- [ ] T011 [P] [US1] `frontend/apps/internal/src/lib/orcamento.ts`: tipos `VagaDoProduto`,
      `ProdutoDeTabela`, `ProdutosEstimativa`, `ProdutoAplicado`; `PricingSettings.produtos?`/
      `produtos_estimativa?`; `CalcularOrcamentoInput.produtos?`; `Quote.produtos?`/`produtos_total?`/
      `coordenadores_inclusos?`/`avisos?`; `OrcamentoFormSnapshot.produtos?`; `MemoriaLinha.tipo` (linha
      :173) ganha `"produto"`; `frontend/apps/internal/src/components/MemoriaDeCalculo.tsx`:
      `FUNDO["produto"]` (fundo próprio) e `FUNDO[linha.tipo] ?? ""`
- [ ] T012 [US1] `frontend/apps/internal/src/components/orcamento/ProdutoLinha.tsx` (NOVO, fonte única
      da linha "📦 <rótulo> — preço de tabela R$ X" / "estimativa", com `brl`) e
      `frontend/apps/internal/src/components/orcamento/ProdutosCard.tsx` (NOVO): `Combobox` de `@manto/ui`
      (options com `description = brl(preco)`, `fallbackIcon` 🎅 por opção, `badge` "inativo" fora da
      lista), botão Adicionar, lista de selecionados com `AnimatePresence` + `useReducedMotion` (usa
      `ProdutoLinha` a partir de `quote.produtos`, vagas incluídas, Remover); props `{produtos,
      selecionados, aplicados, onChange}`
- [ ] T013 [US1] `frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx`: estado `produtos` nos
      cinco lugares (`INITIAL_STATE`, `useState`, `resetAll`, payload/deps, rehydrate
      `snap.produtos?.map(p => ({chave: p.chave})) ?? []`); card `ProdutosCard` no topo da coluna
      direita antes de Equipe; `quote.avisos` em bloco `role="alert"` dourado com borda abaixo da Data (ao
      lado do `DataEspecialAlert`); painel de resultado: quando `quote.produtos.length > 0` e só `show_1h`
      é verdadeiro, mostrar um tile só com o rótulo "preço de tabela"; `ProdutoLinha` junto da nota da
      data especial
- [ ] T014 [P] [US1] `frontend/apps/internal/src/pages/OrcamentoResultadoPage.tsx`: `ProdutoLinha` para
      cada `quote.produtos ?? []`, junto das notas de NF e de data especial; `duracoesVisiveis` já
      respeita `show_Nh`

**Checkpoint**: cenários 2–4 verdes; `/orcamento` mostra R$ 2.500 com o produto em 20/12 e R$ 5.000 em
24/12; `/orcamento/:id` com a linha do produto.

---

## Phase 4: História 2 — A vaga do evento nasce com o teto igual ao cachê combinado (P1)

**Objetivo**: prefill, criação e vínculo 273 com teto 600 / 270 / 250 / 250 (1.000 / 650 / 500 / 250 na
faixa), flat, a partir das vagas congeladas, ordem produto → avulsos → extras; UM Maquiador; casting
rebaixa a 600.

**Verificação da história (obrigatória)**: cenários 8, 9 e 10 em PASS; `/events/new?orcamento_id=`
aberto com o produto Noel + Ajudante.

- [ ] T015 [US2] `app/calendar/routes.py` — `_compute_performer_caches`: `produtos =
      resolver_produtos(snapshot.get("produtos"), …)` a partir das vagas CONGELADAS (chave desconhecida →
      itens com `cache_Nh: None` e nota "produto X não está mais na tabela — teto não aplicado"); emitir
      PRIMEIRO `itens_do_teto(...)` (flat; `has_show=False`; sem `noturno_add` quando `inclui_noturno`;
      com `transport_add`), depois o laço de `performers` como hoje, depois extras: coordenadores dos
      produtos (`coordenadores_do_teto`, pela tabela/faixa com `MARCA_PRODUTO`) → `da_formula`
      genéricos (via `split_coordenadores`, mesmo `min_coordenadores`) → Técnico → UM Maquiador quando há
      make em produto ou avulso, teto `calcular_maquiador(mp + ra, ea)` via `makes_para_maquiador`
- [ ] T016 [US2] `app/calendar/routes.py` — `_build_orcamento_prefill` e
      `app/calendar/orcamento_evento_ops.py` — `_total_da_duracao` (passa a ler `snapshot_do_orcamento
      (entry)`) e `acrescimos_do_orcamento` (duração custom com produto): régua por
      `produtos.total_na_duracao(subtotal_pre_acrescimos(total_4h, …), produtos_total, h, …)`; sem
      `produtos` no snapshot a conta reproduz `total_4h ÷ 4 × h` ao centavo (cenário 7 e regressão 305)
- [ ] T017 [US2] Conferir (sem mudar comportamento) que `_create_roles_from_input`,
      `_create_extra_roles_from_orcamento` e `aplicar_equipe_do_orcamento` toleram `cap None` (sem nota,
      como hoje) e usam a ordem emitida; registrar em `research.md` (D6/D14) o que foi conferido com
      `arquivo:linha`

**Checkpoint**: cenários 8–10 verdes (criação por API, prefill e vínculo com teto 600; dois produtos =
UM Maquiador 300; casting 900 → 600; superadmin 900 → 900).

---

## Phase 5: História 3 — A tabela de preços volta a dizer o cachê (P1)

**Objetivo**: especiais 600/270 em toda carga; sem troca 600→712; inversa guardada; aviso "use o produto".

**Verificação da história (obrigatória)**: cenários 11 e 12 em PASS.

- [ ] T018 [US3] `app/orcamento/quote_ops.py`: `quote["avisos"] = avisos_para(performers, produtos)`
      (aviso do Noel avulso sem produto; aviso de estimativa; aviso de vaga sem cachê) — textos em
      `produtos.py`
- [ ] T019 [US3] Conferir no `manto_local` (só leitura) e registrar em `research.md` (D9) o estado cru da
      tabela depois de T004/T005: `load()` devolve Noel 600 e Ajudante 270; tabela salva com 712 vira 600;
      tabela com 650 fica 650

**Checkpoint**: cenários 11–12 verdes; avulso 20/12 = 2.210 com aviso; 24/12 avulso = 5.010 (faixa 307).

---

## Phase 6: História 4 — O superadmin configura os produtos sem deploy (P2)

**Objetivo**: card "Produtos de tabela" na Configuração de Preços; 400 por campo com foco; inativo e
removido tratados; remoção com `ConfirmDialog`.

**Verificação da história (obrigatória)**: cenários 13, 14 e 17 (DEVE FALHAR) em PASS;
`/orcamento/configuracoes` aberta.

- [ ] T020 [US4] `app/api/orcamento_write.py` — `api_orcamento_settings_save`: ramo `produtos`/
      `produtos_estimativa` DEPOIS do ramo `datas_especiais` (chave AUSENTE no corpo = mantém o salvo) →
      `validar_produtos(..., s["datas_especiais"])` → `json_error("Produtos de tabela inválidos.", 400,
      fields=…)`; `avisos` da validação devolvidos na resposta 200; comentário `RBAC:` inalterado
      (`_require_superadmin`)
- [ ] T021 [US4] `frontend/apps/internal/src/components/orcamento/ProdutosConfigCard.tsx` (NOVO, molde do
      `DatasEspeciaisCard`): por produto — rótulo, descrição, ativo, preço (`MoneyInput`), uma linha de
      preço por faixa existente em `datas_especiais` (vazia = "estimativa na data"), vagas como chips
      (label, tipo via botões, cachê "pela tabela"/valor, maquiagem para especial/ator), `inclui_noturno`,
      Remover produto e remover vaga com `ConfirmDialog` de `@manto/ui`; "Novo produto" (chave slug);
      erros `produtos.<chave>.<campo>` / `vagas.<i>.<campo>` → `aria-invalid` + foco + rótulo legível;
      aviso amarelo para label de especial desconhecido e para faixa órfã; card pequeno "Estimativa"
      para `produtos_estimativa`
- [ ] T022 [US4] `frontend/apps/internal/src/pages/OrcamentoConfigPrecosPage.tsx`: renderizar o
      `ProdutosConfigCard` com `settings.produtos ?? {}`/`produtos_estimativa`; `errosDeSalvar` já cobre;
      rodapé filtra `produtos.*` e `produtos_estimativa.*`; mostrar `avisos` da resposta do save

**Checkpoint**: cenários 13, 14, 17 verdes; tela de configuração com 400 apontando o campo.

---

## Phase 7: História 5 — Produto e itens avulsos convivem no mesmo orçamento (P2)

**Objetivo**: colunas com avulsos × markup + produto fixo; coordenador não em dobro; make incremento;
fora de SP, NF, BV, PIX; régua; personalizado.

**Verificação da história (obrigatória)**: cenários 5, 6 e 7 em PASS.

- [ ] T023 [US5] `app/orcamento/quote_ops.py` + `app/calendar/orcamento_evento_ops.py`: fechar o que a
      T008/T016 deixaram pendente — `resumo_do_orcamento` inclui personagens e makes do produto; conferir
      com o verify que venda, prefill e `_total_da_duracao` dão o MESMO `total_custom` com NF e BV (cenário
      7) e que o BV da duração custom (305) usa a base de `total_na_duracao` quando há produto
- [ ] T024 [US5] `frontend/apps/internal/src/components/orcamento/PerformersEditor.tsx`: prop OPCIONAL
      `coordenadoresInclusos?: number` → texto "N incluído(s) no produto" sob o contador e mínimo do
      contador = inclusos; `OrcamentoCalculadoraPage.tsx` passa `result?.quote.coordenadores_inclusos ??
      0`; EducaManto não passa (neutro)

**Checkpoint**: cenários 5–7 verdes (boneco 4h + Visita; dois produtos; show avulso; make especial; fora
de SP; NF; BV; PIX; 6h com e sem NF/BV; personalizado nos dois critérios).

---

## Phase 8: História 6 — Os tetos 712/423 já gravados são corrigidos (P2)

**Objetivo**: relatório e `--execute` seguros.

**Verificação da história (obrigatória)**: cenário 18 em PASS.

- [ ] T025 [US6] `specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py` (NOVO; `scripts/oneoff/` é
      gitignored — molde `specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py`): relatório
      de `EventRole` com `cache_cap` exatamente 712/423 em eventos `start_at >= 2026-10-16` (qualquer
      nome); `--execute` rebaixa só "Papai Noel"/"Ajudante do Noel" com `cache_value IS NULL AND talent_id
      IS NULL`, acrescenta "(teto corrigido pela 309: {antes} → {depois})" ao `cache_cap_note`, um commit;
      nome diferente / cachê digitado / artista → "não corrigida — conferir à mão"; `MANTO_SEM_THREADS=1`;
      saída UTF-8; docstring com a receita do Shell do Render

**Checkpoint**: cenário 18 verde.

---

## Phase 9: História 7 — O resto não muda (P3)

**Objetivo**: paridade sem `produtos` (gabarito); EducaManto neutro; janela de deploy; regressão 307
(que encadeia a 305).

**Verificação da história (obrigatória)**: cenários 1, 15, 16 e 19 em PASS.

- [ ] T026 [P] [US7] `app/educamanto/quote_ops.py` — `_totais_contratacao`: `payload.pop("produtos",
      None)` ao lado de `event_date` (comentário: FR-016 da 309; o `inputs` do snapshot pode carregar a
      chave, ignorada)
- [ ] T027 [US7] `frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx`: "Gerar Orçamento"
      desabilitado com aviso "O servidor não aplicou o produto — recarregue a página" quando
      `produtos.length > 0` e `result.quote.produtos` é `undefined` (backend velho); integrado ao
      `calcPendente`/`seq` da 307
- [ ] T028 [US7] `specs/307-natal-papai-noel-calculadora/verify_307.py`: config de teste grava Noel
      `[600, 650, 675, 700]` e Ajudante `[270, 320, 345, 370]` e passa a afirmar que a carga NÃO troca para
      712; cenário 1 (:253) → 2.210,00; cenário 2 (:263) → 2.912,00; cenário 10 (:428) → 2.210,00; cenário
      11 (:507-508) tetos 600/270; cenário 12 (:574-578, :652) → Noel 600, Ajudante [270, 320, 345, 370] e a
      inversa 712→600/423→270 age; cenário 15 (:792) → 2.210,00; docstring e `NOEL_ANTIGO` reescritos com
      a mudança de regra (309); rodar `--regressao` verde
- [ ] T029 [US7] Rodar `verify_309.py --regressao` completo → 20/20; guardar a saída final em
      `specs/309-produtos-de-tabela/verify_309_final.txt`

**Checkpoint**: 20/20 com regressão; `verify_307 --regressao` (e a 305 dentro dele) verde.

---

## Phase 10: Polimento e transversais

- [ ] T030 `cd frontend && npm run typecheck` limpo (três SPAs, pelas junções do worktree) e `ruff check`
      em `app/orcamento/`, `app/api/orcamento_write.py`, `app/calendar/routes.py`,
      `app/calendar/orcamento_evento_ops.py`, `app/educamanto/quote_ops.py`,
      `specs/309-…/rebaixar_tetos_noel_309.py`, `specs/309-…/verify_309.py`, `specs/307-…/verify_307.py`; `ruff
      format` só nos arquivos novos
- [ ] T031 Telas abertas no Browser pane (skill `manto-conferir-tela`, `launch.json` `manto-internal` +
      `manto-backend-sem-google`): `/orcamento` (produto em 20/12 e 24/12, valor único, boneco junto,
      aviso do avulso, botão travado simulando `quote.produtos` ausente), `/orcamento/:id`,
      `/orcamento/configuracoes` (400 com foco; `ConfirmDialog` ao remover), `/events/new?orcamento_id=`
      com o produto Noel + Ajudante (tetos 600/270/250/250); restaurar a tabela do `manto_local` se algum
      Salvar persistiu dados de teste
- [ ] T032 Docs por fonte única: `docs/01` (§2.10 `produtos`/`produtos_estimativa`; §3.13 payload
      `produtos`, `quote.produtos`/`produtos_total`/`coordenadores_inclusos`/`avisos`, snapshot com vagas,
      `POST /settings`, memória `produto` + invariante, régua por `total_na_duracao`, especiais 600/270;
      §4.3 as cinco linhas), `docs/02` (`/orcamento`, `/orcamento/:id`, `/orcamento/configuracoes`,
      `/events/new`), `docs/03` (entrada 309 no topo + índice; nota na 307: "712/423 duraram de 16/10 a
      <deploy>"), `docs/04` (linha Orçamento: produto pós-markup; teto a partir das vagas congeladas;
      invariantes; `verify_307` com regra mudada), `docs/05` (quitar #107 pelo script; #103 continua;
      dívidas: cachês visíveis no `/opcoes`, risco aceito preço congelado × teto da faixa,
      `num_colaboradores` vazio → 1 no prefill; #106 com `produtos.py` extraído)
- [ ] T033 `quickstart.md` executado de ponta a ponta; `spec.md` com Status "Implementada em <data>";
      `checklists/dinheiro-e-regressao.md` marcado
- [ ] T034 Commits por caminho no worktree: `feat(309): núcleo` (settings, produtos.py, quote_ops, pdf,
      orcamento_write, educamanto), `feat(309): teto e script` (routes, orcamento_evento_ops,
      specs/309-…/rebaixar_tetos_noel_309.py), `feat(309): telas` (frontend), `docs(309): …` (specs +
      docs); nunca `git add -A`
- [ ] T035 `/speckit-converge` (workflow: leitores por história + cético) e aplicar os achados como
      `fix(309): converge`. Depois, **só quando o dono pedir**: merge `--no-ff` na `main` + `git push
      origin main` a partir das ~19h (a partir do worktree; `git -C` no principal só se ele estiver limpo
      e na `main`); antes de "em produção": `git status --short` limpo, `git log -1` = cabeçalho do
      `docs/03`, `migrations/versions/` sem untracked, sonda `/api/` com JSON; pós-deploy: conferência só
      de leitura por SSH (Noel 600, Ajudante 270, `produtos` padrão, produto 20/12 = 2.500 e 24/12 =
      5.000), script dos tetos (dry-run → `--execute` → zero), aviso à equipe (Visita = produto; sem
      "Papai Noel" avulso para visita; sem acréscimo "Outro")

---

## Dependências e ordem

- Setup (T001) → Foundational (T002–T007; T002/T003 antes de T004–T007) → US1 (T008–T014) → US2
  (T015–T017) → US3 (T018–T019) → US4 (T020–T022) → US5 (T023–T024) → US6 (T025) → US7 (T026–T029) →
  Polimento (T030–T035)
- Intra-história: T011, T012 → T013 → T024, T027; T008 → T009, T010; T015 → T016 → T023; T020 → T021 →
  T022
- US2 depende de T007 e T008 (snapshot com `produtos` congelados); US5 depende de T008 e T015; US7
  depende de tudo
- Paralelos: T010 ∥ T011 ∥ T012 (arquivos diferentes) depois de T008; T014 ∥ T013; T026 ∥ T027; T021 ∥
  T020
- O verify (T002) é escrito e roda vermelho (T003) ANTES de T004 — e o gabarito do cenário 1 só vale se
  gravado nessa rodada, antes de qualquer mudança de código
- Entre T004 e T028 o `verify_307` fica vermelho (afirma 712): consequência esperada; a regressão só
  fecha em T028/T029

## Estratégia

- **MVP primeiro**: Setup + Foundational + US1 (preço de tabela na venda) + US2 (teto honesto) + US3
  (especiais 600/270) — são as três P1 e já resolvem o dinheiro; US4–US7 fecham configuração,
  convivência, script e regressão
- **Incremental**: cada história deixa o verify mais verde sem quebrar a anterior; commit por grupo
  lógico (`feat(309):`), sempre por caminho, no worktree
- Deploy só quando o dono pedir, fora do horário da equipe
