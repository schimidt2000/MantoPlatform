---
description: "Tasks da feature 309 — Produtos de tabela (Visita Mágica pelo preço da tabela de venda)"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: Produtos de tabela — a Visita Mágica vendida pelo preço da tabela de venda

**Input**: artefatos em `/specs/309-produtos-de-tabela/` (worktree `C:\tmp\mp309`, branch
`309-produtos-de-tabela`; a árvore principal está com a 308 de outro chat — nada é escrito lá)

**Pré-requisitos**: plan.md, spec.md (7 histórias e a tabela "Verificação"), research.md (D1–D20),
data-model.md, contracts/api.md, quickstart.md

**Verificação (OBRIGATÓRIA neste projeto — constituição, Princípio VIII)**: `verify_309.py` é escrito na
fase Foundational, ANTES do núcleo, rodado VERMELHO (saída em `verify_309_primeira_falha.txt`) e passa
história a história. Não existe pytest nem `tests/`.

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
  `app/educamanto/quote_ops.py` · `app/calendar/{routes,orcamento_evento_ops}.py` · `scripts/oneoff/`
- Frontend: `frontend/apps/internal/src/{lib/orcamento.ts, components/MemoriaDeCalculo.tsx,
  components/orcamento/, pages/}`
- Verificação: `specs/309-produtos-de-tabela/verify_309.py`; regressão `specs/307-…/verify_307.py` e
  `specs/305-…/verify_305.py`

## Phase 1: Setup

- [ ] T001 Conferir o estado de partida e registrar em `specs/309-produtos-de-tabela/research.md` (seção
      "Estado de partida"): no `manto_local`, `pricing_config` cru (especiais Papai Noel/Ajudante, há
      `produtos`?), markup receptivo 1h, coordenador 1h, `maquiador.make_1`, faixa `natal`; `git log -1`
      do worktree; junções de `node_modules` no worktree funcionando (`cd frontend && npm run typecheck`
      roda) — tudo só leitura

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [ ] T002 **`specs/309-produtos-de-tabela/verify_309.py`** — os 20 cenários da tabela "Verificação" da
      spec, no molde de `verify_307.py`: config real salva/restaurada por conexão separada; config de
      teste determinística (markup 2,6/2,5/2,45/2,4, coordenador 250/300/325/350, `make_1` 250, especiais
      Papai Noel `[712, 800, 850, 900]` e Ajudante `[423, 480, 510, 540]` GRAVADOS para provar a inversa,
      SEM `produtos` para provar os padrões, faixa `natal` da 307); usuários descartáveis `__v309_` sa /
      com / casting (login só por `POST /api/auth/login`); evento descartável só pela API com Google
      suprimido e roles criadas/apagadas na mesma rodada; cenário 17 DEVE FALHAR (COMERCIAL 403);
      cenário 19 (`--regressao`) roda `verify_307.py --regressao` e `verify_305.py --regressao` em
      subprocesso; cenário 20 limpa e confere a restauração; `--so=…`
- [ ] T003 Rodar o verify ANTES do núcleo e guardar a saída em
      `specs/309-produtos-de-tabela/verify_309_primeira_falha.txt` — esperado: 2–15 e 18 FALHAM pelos
      motivos certos (chave `produtos` ignorada → 2.210; sem `quote.produtos`; carga ainda entrega 712;
      script inexistente), 1 e 17 passam
- [ ] T004 `app/orcamento/settings.py`: DEFAULTS — `especiais["Papai Noel"] = [600, 650, 675, 700]`,
      `especiais["Ajudante do Noel"] = [270, 320, 345, 370]`; bloco `produtos` com os dois padrão
      (`visita_magica`, `visita_magica_ajudante` conforme `data-model.md` §1) e `produtos_estimativa =
      {"fator_cache": 2.0, "markup": 3.0}`; constantes `TIPOS_DE_VAGA`, `PRODUTO_ROTULO_MAX = 60`,
      `PRODUTO_DESCRICAO_MAX = 120`, `PRODUTO_VAGAS_MAX = 10`, `NOEL_712 = [712, 800, 850, 900]`,
      `AJUDANTE_423 = [423, 480, 510, 540]`; apagar `PAPAI_NOEL_CACHE_ANTIGO` e o bloco de troca 600→712
      de `_migrar_307` (comentário com o porquê: 309)
- [ ] T005 `app/orcamento/settings.py`: `_migrar_309(data)` — `setdefault` de `produtos` e
      `produtos_estimativa` só com chave AUSENTE; `_normalizar_produto` defensivo (descarta produto/vaga
      malformados e `por_faixa` de faixa inexistente; nunca preço 0; `isinstance` em tudo); troca
      inversa guardada (`== NOEL_712` → 600…, `== AJUDANTE_423` → 270…); chamado por `_migrate` depois de
      `_migrar_307`; docstring: roda dentro do `try` de `load()`
- [ ] T006 `app/orcamento/settings.py`: `validar_produtos(bloco, estimativa, especiais, datas_especiais)
      -> tuple[dict, dict]` levantando `SettingsValidationError` com `fields` `produtos.<chave>.<campo>`
      (regras e mensagens da tabela de `contracts/api.md`; `produtos_estimativa.fator_cache` e `.markup`
      juntos); label de especial desconhecido NÃO é erro
- [ ] T007 `app/orcamento/produtos.py` (NOVO, puro, com docstring do porquê e type hints):
      `resolver_produtos(selecao, cfg, faixa) -> list[ProdutoResolvido]` (chave desconhecida →
      `ProdutoDesconhecido(chave)`), `preco_do_produto(produto, faixa, cfg) -> (preco, faixa_chave,
      estimado)` (regra de `data-model.md` §2), `cache_da_vaga(vaga, faixa, cfg, has_show) -> float |
      None` (tabela de resolução do §1; label de especial inexistente → `None`),
      `coordenadores_dos_produtos(produtos) -> int`, `makes_dos_produtos(produtos) -> int`,
      `itens_do_teto(produtos, faixa, cfg, has_show, transport_add) -> list[dict]` (shape de
      `contracts/api.md` "Item do teto", flat, `origem: "produto"`), `produtos_total(produtos) -> float`;
      constantes de rótulo (`MARCA_PRODUTO`, textos dos avisos)

**Checkpoint**: verify vermelho pelos motivos certos; tabela com os padrões e a inversa; fonte única
pronta e sem consumidor.

---

## Phase 3: História 1 — A vendedora vende a Visita Mágica pelo preço da tabela (P1) 🎯 MVP

**Objetivo**: produto selecionado → 2.500 / 3.600 (5.000 / 6.500 em 24/25) iguais nas quatro colunas;
memória, mensagem e PDF com a linha do produto; `quote.produtos`/`snapshot.produtos`.

**Verificação da história (obrigatória)**: cenários 2, 3, 4 e 12 (parte do avulso) em PASS; tela
`/orcamento` e `/orcamento/:id` abertas.

- [ ] T008 [US1] `app/orcamento/quote_ops.py` — `calculate_quote`: ler `payload.get("produtos")`,
      `produtos = resolver_produtos(...)` com `cfg_precos`/`faixa` já carregados (erro →
      `QuoteValidationError("produtos", …)`); `coord_produtos`/`coordenador_qty_total` (D11) antes do
      laço; depois de "= Após markup": `totals[i] += produtos_total`, linhas `tipo "produto"` (label =
      rótulo; detalhe "preço de tabela" | "preço de tabela · <rótulo da faixa>" | "preço estimado (sem
      preço de <faixa>)"), linha subtotal "= Após produtos"; noturno conta só avulsos + coordenadores da
      fórmula quando `inclui_noturno`; `team_lines` com os labels `especial`/`ator` do produto;
      `quote["produtos"]`, `quote["produtos_total"]`, `quote["avisos"]`; `snapshot["produtos"]`
      (`{chave, preco_aplicado, faixa_chave, estimado}`) e `snapshot["produtos_total"]`
- [ ] T009 [US1] `app/orcamento/quote_ops.py` — mensagem WhatsApp: bloco do produto antes do bloco de
      durações ("Visita Mágica — Papai Noel (visita padrão (até 1h)): R$ 2.500,00"; "(estimativa)"
      quando `estimado`); `_dur_block` continua; `_rotulo_da_faixa` reusado
- [ ] T010 [P] [US1] `app/orcamento/pdf.py`: linha do produto (rótulo, descrição, preço aplicado,
      "(estimativa)") depois da lista da equipe, antes da nota de deslocamento; lê `quote.get("produtos")
      or []` (legado sem a chave)
- [ ] T011 [P] [US1] `frontend/apps/internal/src/lib/orcamento.ts`: tipos `VagaDoProduto`,
      `ProdutoDeTabela`, `ProdutosEstimativa`; `PricingSettings.produtos?`/`produtos_estimativa?`;
      `CalcularOrcamentoInput.produtos?`; `Quote.produtos?`/`produtos_total?`/`avisos?`;
      `OrcamentoFormSnapshot.produtos?`; `MemoriaLinha.tipo` ganha `"produto"`;
      `frontend/apps/internal/src/components/MemoriaDeCalculo.tsx`: `FUNDO["produto"]` (fundo próprio) e
      `FUNDO[linha.tipo] ?? ""`
- [ ] T012 [US1] `frontend/apps/internal/src/components/orcamento/ProdutosCard.tsx` (NOVO): `Combobox` de
      `@manto/ui` (clearable, `fallbackIcon`, options = produtos `ativo` com description = `brl(preco)`),
      botão Adicionar, lista de selecionados com `AnimatePresence` + `useReducedMotion` (rótulo, chip
      "preço de tabela"/"estimativa" vindo de `quote.produtos`, vagas incluídas, Remover); props
      `{produtos, selecionados, aplicados, onChange}`
- [ ] T013 [US1] `frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx`: estado `produtos` nos
      cinco lugares (`INITIAL_STATE`, `useState`, `resetAll`, payload/deps, rehydrate
      `snap.produtos?.map(p => ({chave: p.chave})) ?? []`); card `ProdutosCard` no topo da coluna
      direita antes de Equipe; `quote.avisos` em lista dourada abaixo da Data (ao lado do
      `DataEspecialAlert`); painel de resultado: quando `quote.produtos.length > 0` e as quatro durações
      são iguais, mostrar um valor só com o rótulo "preço de tabela"; linha "📦 <rótulo> — preço de
      tabela R$ X" (ou "estimativa") junto da nota da data especial
- [ ] T014 [P] [US1] `frontend/apps/internal/src/pages/OrcamentoResultadoPage.tsx`: linha "📦 <rótulo> —
      preço de tabela R$ X" (ou "(estimativa)") para cada `quote.produtos`, junto das notas de NF e de
      data especial; `quote.produtos ?? []`

**Checkpoint**: cenários 2–4 verdes; `/orcamento` mostra R$ 2.500 com o produto em 20/12 e R$ 5.000 em
24/12; `/orcamento/:id` com a linha do produto.

---

## Phase 4: História 2 — A vaga do evento nasce com o teto igual ao cachê combinado (P1)

**Objetivo**: prefill, criação e vínculo 273 com teto 600 / 270 / 250 / 250 (1.000 / 650 / 500 / 250 na
faixa), flat, ordem produto → avulsos → extras; casting rebaixa a 600.

**Verificação da história (obrigatória)**: cenários 8, 9 e 10 em PASS; `/events/new?orcamento_id=`
aberto.

- [ ] T015 [US2] `app/calendar/routes.py` — `_compute_performer_caches`: ler `snapshot.get("produtos")`,
      `produtos = resolver_produtos(...)` (desconhecido → item com `cache_Nh: None` e `cap_notes`
      "produto X não está mais na tabela — teto não aplicado"); emitir PRIMEIRO `itens_do_teto(...)`
      (flat; sem `noturno_add` quando `inclui_noturno`; com `transport_add`), depois o laço de
      `performers` como hoje, depois extras: coordenadores dos produtos (pela tabela/faixa, `cap_note` do
      produto) → `coordenador_qty_total − coord_produtos` genéricos → Técnico → Maquiador (a vaga do
      produto substitui a genérica; teto = `calcular_maquiador(makes_produto + makes_avulsos)`);
      `_montar_cap_note` com "produto <rótulo>"
- [ ] T016 [US2] `app/calendar/routes.py` — `_build_orcamento_prefill` e
      `app/calendar/orcamento_evento_ops.py` — `_total_da_duracao`: régua com `produtos_total` do snapshot
      (`(total_4h − produtos_total) ÷ 4 × h + produtos_total`); snapshot sem a chave → `produtos_total =
      0` (conta de hoje)
- [ ] T017 [US2] Conferir (sem mudar comportamento) que `_create_roles_from_input`,
      `_create_extra_roles_from_orcamento` e `aplicar_equipe_do_orcamento` toleram `cap None` e usam a
      ordem emitida; ajustar só `cap_note` se faltar; registrar em `research.md` (D6/D14) o que foi
      conferido com `arquivo:linha`

**Checkpoint**: cenários 8–10 verdes (criação por API, prefill e vínculo com teto 600; casting 900 → 600;
superadmin 900 → 900).

---

## Phase 5: História 3 — A tabela de preços volta a dizer o cachê (P1)

**Objetivo**: especiais 600/270 em toda carga; sem troca 600→712; inversa guardada; aviso "use o produto".

**Verificação da história (obrigatória)**: cenários 11 e 12 em PASS.

- [ ] T018 [US3] `app/orcamento/quote_ops.py`: aviso em `quote["avisos"]` quando há `especial "Papai
      Noel"` em `performers` e `produtos` vazio ("Para a Visita Mágica use o produto de tabela em vez do
      item \"Papai Noel\".") — texto em `produtos.py`
- [ ] T019 [US3] Conferir no `manto_local` (só leitura) e registrar em `research.md` (D9) o estado cru da
      tabela depois de T004/T005: `load()` devolve Noel 600 e Ajudante 270; tabela salva com 712 vira 600;
      tabela com 650 fica 650

**Checkpoint**: cenários 11–12 verdes; avulso 20/12 = 2.210 com aviso; 24/12 avulso = 5.010 (faixa 307).

---

## Phase 6: História 4 — O superadmin configura os produtos sem deploy (P2)

**Objetivo**: card "Produtos de tabela" na Configuração de Preços; 400 por campo com foco; inativo e
removido tratados.

**Verificação da história (obrigatória)**: cenários 13, 14 e 17 (DEVE FALHAR) em PASS;
`/orcamento/configuracoes` aberta.

- [ ] T020 [US4] `app/api/orcamento_write.py` — `api_orcamento_settings_save`: ramo `produtos`/
      `produtos_estimativa` (chave AUSENTE no corpo = mantém o salvo) → `validar_produtos` →
      `json_error("Produtos de tabela inválidos.", 400, fields=…)`; comentário `RBAC:` inalterado
      (`_require_superadmin`)
- [ ] T021 [US4] `frontend/apps/internal/src/components/orcamento/ProdutosConfigCard.tsx` (NOVO, molde do
      `DatasEspeciaisCard`): por produto — rótulo, descrição, ativo, preço (`MoneyInput`), uma linha de
      preço por faixa existente em `datas_especiais` (vazia = "estimativa na data"), vagas como chips
      (label, tipo via botões/Combobox se > 10, cachê "pela tabela"/valor), `inclui_noturno`, Remover
      (confirm); "Novo produto" (chave slug); erros `produtos.<chave>.<campo>` → `aria-invalid` + foco +
      rótulo legível; aviso amarelo para label de especial desconhecido; card pequeno "Estimativa" para
      `produtos_estimativa`
- [ ] T022 [US4] `frontend/apps/internal/src/pages/OrcamentoConfigPrecosPage.tsx`: renderizar o
      `ProdutosConfigCard` com `settings.produtos ?? {}`/`produtos_estimativa`; `errosDeSalvar` já cobre;
      rodapé filtra `produtos.*`; "Remover" especial não precisa limpar produtos (vaga por label não é
      erro de save)

**Checkpoint**: cenários 13, 14, 17 verdes; tela de configuração com 400 apontando o campo.

---

## Phase 7: História 5 — Produto e itens avulsos convivem no mesmo orçamento (P2)

**Objetivo**: colunas com avulsos × markup + produto fixo; coordenador não em dobro; make incremento;
fora de SP, NF, BV, PIX; régua; personalizado.

**Verificação da história (obrigatória)**: cenários 5, 6 e 7 em PASS.

- [ ] T023 [US5] `app/orcamento/quote_ops.py`: maquiador — venda cobra `calcular_maquiador(makes_produto
      + makes_avulsos) − calcular_maquiador(makes_produto)` × 1,5 (incremento; zero quando só o produto);
      régua `total_custom = (totals[3] − produtos_total) ÷ 4 × h + produtos_total`; personalizado
      `valor_final` remove as linhas `produto` e `= Após produtos` da memória filtrada; `multiplicador`
      → `totals = cache_base × mult + produtos_total` com a linha `produto` depois de "× Multiplicador";
      `num_going` inclui as pessoas do produto (van); acréscimos/NF/PIX inalterados (incidem sobre o total
      com produto)
- [ ] T024 [US5] `frontend/apps/internal/src/components/orcamento/PerformersEditor.tsx`: prop OPCIONAL
      `coordenadoresInclusos?: number` → texto "N incluído(s) no produto" sob o contador e mínimo do
      contador = inclusos; `OrcamentoCalculadoraPage.tsx` passa `coord_produtos` lido de
      `quote.produtos[].vagas`; EducaManto não passa (neutro)

**Checkpoint**: cenários 5–7 verdes (boneco 4h + Visita; dois produtos; fora de SP; NF; BV; PIX; 6h;
personalizado nos dois critérios).

---

## Phase 8: História 6 — Os tetos 712/423 já gravados são corrigidos (P2)

**Objetivo**: relatório e `--execute` seguros.

**Verificação da história (obrigatória)**: cenário 18 em PASS.

- [ ] T025 [US6] `specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py` (NOVO; `scripts/oneoff/` é
      gitignored — molde `specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py`):
      seleção `EventRole.character_name ∈ {Papai Noel, Ajudante do Noel}`, `cache_cap` exatamente
      712/423, evento `start_at >= 2026-10-16`; relatório por linha (evento, data, vaga, teto, cachê,
      artista, ação); `--execute` rebaixa só `cache_value IS NULL AND talent_id IS NULL`, acrescenta
      "(teto corrigido pela 309: 712 → 600)" ao `cache_cap_note`, um commit; `MANTO_SEM_THREADS=1`;
      saída UTF-8; docstring com a receita do Shell do Render

**Checkpoint**: cenário 18 verde (vaga descartável 712 → 600; vaga com cachê/artista intocada e listada).

---

## Phase 9: História 7 — O resto não muda (P3)

**Objetivo**: paridade sem `produtos`; EducaManto neutro; janela de deploy; regressão 305/307.

**Verificação da história (obrigatória)**: cenários 1, 15, 16 e 19 em PASS.

- [ ] T026 [P] [US7] `app/educamanto/quote_ops.py` — `_totais_contratacao`: `payload.pop("produtos",
      None)` ao lado de `event_date` (comentário: FR-016 da 309)
- [ ] T027 [US7] `frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx`: "Gerar Orçamento"
      desabilitado com aviso "O servidor não aplicou o produto — recarregue a página" quando
      `produtos.length > 0` e `result.quote.produtos` é `undefined` (backend velho); integrado ao
      `calcPendente`/`seq` da 307
- [ ] T028 [US7] `specs/307-natal-papai-noel-calculadora/verify_307.py`: config de teste grava Noel
      `[600, 650, 675, 700]` e passa a afirmar que a carga NÃO troca para 712; cenário 1 → 2.210,00;
      cenário 2 → 2.912,00; cenário 11 teto 20/12 → 600/270; cenário 12 → migração não injeta 712 e a
      inversa 712→600 age; cabeçalho da docstring com a mudança de regra (309); rodar `--regressao` verde
- [ ] T029 [US7] Rodar `verify_309.py --regressao` completo → 20/20; guardar a saída final em
      `specs/309-produtos-de-tabela/verify_309_final.txt`

**Checkpoint**: 20/20 com regressão; `verify_305` e `verify_307` verdes.

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
      `/orcamento/configuracoes` (400 com foco), `/events/new?orcamento_id=` (tetos 600/250/250); restaurar
      a tabela do `manto_local` se algum Salvar persistiu dados de teste
- [ ] T032 Docs por fonte única: `docs/01` (§2.10 `produtos`/`produtos_estimativa`; §3.13 payload
      `produtos`, `quote.produtos`/`avisos`, snapshot, `POST /settings`, memória `produto`, especiais
      600/270; §4.3 linhas atualizadas), `docs/02` (`/orcamento`, `/orcamento/:id`,
      `/orcamento/configuracoes`, `/events/new`), `docs/03` (entrada 309 no topo + índice; nota na 307:
      "712/423 duraram de 16/10 a <deploy>"), `docs/04` (linha Orçamento: produto pós-markup; teto pela
      tabela; invariantes; `verify_307` com regra mudada), `docs/05` (quitar #107 pelo script; #103
      continua; dívida: cachês visíveis no `/opcoes`; #106 com `produtos.py` extraído)
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
- US2 depende de T007 e T008 (snapshot com `produtos`); US5 depende de T008 e T015; US7 depende de tudo
- Paralelos: T010 ∥ T011 ∥ T012 (arquivos diferentes) depois de T008; T014 ∥ T013; T026 ∥ T027; T021 ∥ T020
- O verify (T002) é escrito e roda vermelho (T003) ANTES de T004

## Estratégia

- **MVP primeiro**: Setup + Foundational + US1 (preço de tabela na venda) + US2 (teto honesto) + US3
  (especiais 600/270) — são as três P1 e já resolvem o dinheiro; US4–US7 fecham configuração,
  convivência, script e regressão
- **Incremental**: cada história deixa o verify mais verde sem quebrar a anterior; commit por grupo
  lógico (`feat(309):`), sempre por caminho, no worktree
- Deploy só quando o dono pedir, fora do horário da equipe
