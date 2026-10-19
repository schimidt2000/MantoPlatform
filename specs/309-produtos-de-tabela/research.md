# Research — 309 Produtos de tabela

> Phase 0 do `/speckit-plan`. Não havia NEEDS CLARIFICATION na spec (as dúvidas foram fechadas pelo dono
> em 19/10 — Clarifications); este arquivo registra as decisões técnicas, com alternativas, a partir do
> plano de análise (3 desenhos × 3 céticos, `wf_21e30e2c-5fe`) e dos mapas de código (HEAD `6356b80`).

## D1 — Produto é chave própria do payload, não um tipo de performer

- **Decisão**: `payload["produtos"] = [{"chave": "visita_magica"}]`, ao lado de `performers`;
  `snapshot["produtos"]` congela `{chave, preco_aplicado, faixa_chave, estimado}`.
- **Razão**: qualquer `type` desconhecido em `performers` cai no `else` de `quote_ops.py:262-264`
  (preço 0, label "Profissional") e ainda conta no noturno (`:321`) — um backend velho na janela de
  deploy cobraria R$ 0 + 50 pelo produto. Chave separada, o backend velho simplesmente ignora, e o
  EducaManto fica neutro com um `pop` (`educamanto/quote_ops.py:123`, ao lado de `event_date`).
- **Alternativas**: tipo `pacote` em `performers` (rejeitada: acima); pré-popular `performers` com Noel
  + Ajudante ao escolher o produto (rejeitada: o produto deixaria de ser identificável no snapshot e o
  preço voltaria a sair da fórmula).

## D2 — O preço do produto entra depois do markup e antes dos itens pós-markup

- **Decisão**: `totals[i] += Σ preco_aplicado` logo após a linha "= Após markup" (`quote_ops.py:313`)
  e antes de brinde/noturno/técnico/maquiador/transporte/acréscimos/NF (`:315-442`).
- **Razão**: acréscimos % (BV da 305, `valores_brl`), NF ÷ 0,84 e a `_conta_inversa` do evento
  (`orcamento_evento_ops.py:211-229`) só continuam batendo se o produto já estiver em `totals` quando
  eles incidem. Fora de SP (262) soma por cima, como pedido.
- **Alternativas**: somar no fim (rejeitada: BV e NF deixariam de incidir sobre o produto e a conta
  inversa quebraria); substituir `cache_totals` (rejeitada: multiplicaria o produto pelo markup).

## D3 — Preço fixo por visita (escalar), igual nas quatro colunas, fora da régua

- **Decisão (dono)**: `preco: 2500` (um número). Entra igual em `total_1h..4h`; régua >4h:
  `total_custom = (total_4h − produtos_total) ÷ 4 × h + produtos_total` em `quote_ops.py:444-446`,
  `_build_orcamento_prefill` (`routes.py:3248-3253`) e `_total_da_duracao`
  (`orcamento_evento_ops.py:160-169`) — os três leem `produtos_total` do snapshot.
- **Razão**: "esse valor é para uma visita padrão, com tempo e roteiro pré-determinados; evento de 3h
  com Noel vai para o cálculo normal". Evita inventar 2h–4h (2.750/2.880/3.000 e 10.000/15.000/20.000
  que os arquitetos propuseram não existem na tabela do dono).
- **Alternativas**: `preco[4]` por duração (rejeitada pelo dono); `preco` com 0 = "não vendido"
  (rejeitada: numa festa de 4h + Visita apagaria as colunas dos avulsos — achado do cético).

## D4 — Fonte única `app/orcamento/produtos.py`

- **Decisão**: módulo puro com `resolver_produtos(selecao, cfg, faixa)`, `preco_do_produto(produto,
  faixa, cfg)` (inclui a estimativa), `vagas_do_produto(produto, faixa, cfg, has_show)` → itens no shape
  de `_compute_performer_caches` e `coordenadores_dos_produtos(produtos)`. `calculate_quote` e
  `_compute_performer_caches` chamam as mesmas funções com `cfg_precos`/`faixa` já carregados.
- **Razão**: a 307 provou o padrão com `cache_na_faixa` — duas leituras paralelas de `performers`
  (`quote_ops.py:205-274` × `routes.py:2904-3011`) só ficam coerentes com uma função no meio.
- **Alternativas**: lógica inline nos dois lugares (rejeitada: diverge e piora #106).

## D5 — Cachê da vaga `null` = pela tabela vigente na data

- **Decisão**: `cache: null` resolve pela tabela com a faixa da data do evento — especial →
  `get_especial_prices(label, show=False, faixa=)` + `cache_na_faixa`; coordenador →
  `get_coordenador_prices(has_show, 1, faixa)`; maquiador → `calcular_maquiador(1)` (`make_1`); ator →
  `get_ator_prices`. Coluna 1h (a visita é uma unidade), replicada nas 4 colunas (flat). `cache: 650`
  (número) fixa quando divergir.
- **Razão**: uma fonte só para o cachê — o dono edita Noel 600/1.000 em Itens Especiais/Datas especiais e
  o produto só sabe de preço e composição; evita a duplicação `datas_especiais.natal.cache` ×
  `produto.vagas` (cético: "mesmo artista, mesmo dia, dois tetos").
- **Alternativas**: cachê explícito por vaga em todo produto (rejeitada: duplica e desatualiza);
  referência por nome de especial com órfãos (rejeitada: a 307 mostrou que nome órfão leva a 400 em
  todo Salvar — aqui `label` desconhecido na tabela vira "sem teto com aviso", nunca erro de save).

## D6 — Ordem de emissão: produtos → avulsos → extras; prefill = criação

- **Decisão**: `_compute_performer_caches` emite primeiro as vagas `character` dos produtos (na ordem da
  seleção e da composição), depois os `performers` como hoje (`routes.py:2905-3011`), depois os extras
  (coordenadores dos produtos, coordenadores genéricos, Técnico, Maquiador) — mesma função para o
  prefill (`:3245-3247`) e para a criação (`:3802-3816`), então o pareamento posicional
  `characters[i] ↔ orc_chars[i]` (`:3508-3523`) continua válido. Vínculo 273 casa por nome
  (`orcamento_evento_ops.py:685-689`).
- **Razão**: o React do `EventCreatePage` mapeia `caches` com `role_type "character"` na ordem recebida
  (`:218-229`); qualquer ordem diferente entre prefill e criação herdaria o teto de outra vaga.
- **Alternativas**: casar por nome também na criação (rejeitada: mudança no fluxo da 236/273 fora de
  escopo).

## D7 — Noturno embutido no produto

- **Decisão (dono)**: `inclui_noturno: true` (padrão) → o adicional de R$ 50/pessoa (`quote_ops.py:320-326`)
  conta só `performers` + coordenadores da fórmula; o teto das vagas do produto não soma `noturno_add`
  (`routes.py:2878-2884, 2976-2979`). Avulsos continuam somando.
- **Razão**: a tabela de venda é o preço; o pago de 2025 (600) não dependia da hora; quase toda visita
  de 24/12 é à noite — somar daria 5.100/6.650 ao cliente e teto 1.050/700/550.
- **Alternativas**: somar como hoje (rejeitada pelo dono); flag por produto `false` continua possível.

## D8 — Produto sem preço na faixa da data → estimativa marcada

- **Decisão (dono, clarify)**: `preco_estimado = Σ cache_1h das vagas pela tabela NORMAL ×
  produtos_estimativa.fator_cache (2,0) × produtos_estimativa.markup (3,0)`; `estimado: true` no
  quote/snapshot; linha da memória "preço estimado (sem preço de <faixa>)"; "(estimativa)" na mensagem
  e no PDF; aviso dourado forte. O teto das vagas segue a tabela na data (faixa), não a estimativa.
- **Razão**: "estimar custo de cachê dobrado e markup um pouco mais alto que o padrão" — nunca o preço
  normal em silêncio (cético: "pior silêncio possível"), nunca bloqueio.
- **Alternativas**: exigir no cadastro e bloquear (recomendada por mim, rejeitada pelo dono); vender
  pelo normal com aviso (rejeitada).

## D9 — Especiais voltam a dizer o cachê; troca 600→712 sai; inversa guardada

- **Decisão**: DEFAULTS `Papai Noel [600, 650, 675, 700]`, `Ajudante do Noel [270, 320, 345, 370]`
  (`settings.py:93-96`); `_migrar_307` (`:511-534`) perde o bloco que troca `PAPAI_NOEL_CACHE_ANTIGO`
  → 712; `_migrar_309` troca `[712, 800, 850, 900]` → 600 e `[423, 480, 510, 540]` → 270 SÓ se o valor
  salvo for exatamente esse (padrão Transformer→BGE). Os dois especiais ficam; aviso "Para a Visita
  Mágica use o produto" quando Papai Noel entra avulso sem produto (`quote.avisos`).
- **Razão**: cachê é cachê (dono). Excluir os especiais em 2026 faria orçamento pré-309 com o especial
  virar evento com teto 0 (`get_especial_prices` devolve zeros para personagem fora da tabela,
  `pricing.py:157-169`; `routes.py:2944`).
- **Premissa conferida em produção (16/10)**: a tabela salva ainda tem Noel `600/650/675/700` cru (a
  troca só existia em memória) — a inversa guardada é quase sempre no-op; se alguém salvou a tabela
  migrada, ela age.

## D10 — Memória: linha tipo `produto`; personalizado; multiplicador

- **Decisão**: tipo novo `produto` na união `MemoriaLinha.tipo` (`lib/orcamento.ts:169-174`) e em
  `FUNDO` (`MemoriaDeCalculo.tsx:19-25`); linha por exemplar depois de "= Após markup", `valores` iguais
  nas 4 colunas; linha de "= Após produtos" (subtotal). Personalizado `valor_final`: a filtragem da
  memória (`quote_ops.py:448-476`) remove as linhas `produto` (o digitado vence; hotfix 210 continua);
  `multiplicador`: `totals = cache_base × mult + produtos_total`, com a linha `produto` depois de
  "× Multiplicador".
- **Razão**: a soma das linhas tem de fechar com o TOTAL (cen_16 da 307); tipo explícito > reaproveitar
  `pos`/`cache` (que entrariam em `Σcache × markup`).
- **Alternativas**: tipo `info` (existe no comentário, nunca emitido; `FUNDO` não o tem).

## D11 — Coordenador: regra única de split

- **Decisão**: `coord_produtos = Σ vagas tipo coordenador dos produtos`; `coordenador_qty_total =
  max(payload.coordenador_qty, coord_produtos)` (depois de `min_coordenadores`, `quote_ops.py:122-134`);
  `coordenadores_da_formula = coordenador_qty_total − coord_produtos` entram em
  `get_coordenador_prices(has_show, n, faixa)` (`:285-287`); no teto, os `coord_produtos` primeiros
  saem "pela tabela na data" com `cap_note` do produto e os demais como hoje (`routes.py:3015-3047`).
  `_ensure_coordinator` (`:2080-2092`) não cria vaga extra porque o produto já traz Coordenador.
- **Razão**: sem isso o produto cobra 250 × 2,6 por cima dos 2.500 e cria duas vagas.
- **Alternativas**: produto sem coordenador (rejeitada: a Visita tem coordenador; teto 250/500 vem da
  tabela).

## D12 — Maquiador incluso; make de avulso é incremento

- **Decisão (dono)**: a vaga Maquiador do produto nasce pela tabela (`make_1` 250), sem cobrar à parte
  no preço; makes de avulsos no mesmo orçamento: venda cobra `calcular_maquiador(makes_produto +
  makes_avulsos) − calcular_maquiador(makes_produto)` × 1,5 (incremento), teto da vaga única =
  `calcular_maquiador(total)`. Noel do produto tem `needs_makeup: true` para o vínculo 273 marcar a
  vaga.
- **Razão**: 2025 pagou make em 4 de 5 visitas dentro dos 2.500; cliente não paga duas vezes.

## D13 — Teto honesto; cachê continua nascendo vazio

- **Decisão**: nada muda em `casting_ops.assign_role` (`:117-132`), `agenda_read._serialize_role`
  (`:326-348`) nem na criação (`routes.py:3518-3523`): `cache_value` vazio, `cache_cap` = cachê do
  produto. Sem piso.
- **Razão**: decisão 4 da 236 e invariante da 238 preservados; "paga o teto" vira pagar o combinado.
- **Alternativas**: pré-preencher `cache_value` (rejeitada: contraria a 236 e ancora o casting); piso
  no casting (fora de escopo, regra nova).

## D14 — Produto apagado depois da venda

- **Decisão**: venda → `QuoteValidationError("produtos", 'O produto "X" não está mais na tabela…')`
  (molde `:238-243`); teto (prefill/criação/vínculo) → as vagas do produto saem com `cache_Nh = None` e
  `cap_note` "produto X não está mais na tabela — teto não aplicado"; `_create_roles_from_input` e
  `aplicar_equipe_do_orcamento` já toleram cap `None` (`routes.py:3523`; `orcamento_evento_ops.py:701-704`).
  Produto `ativo: false` continua resolvendo (some só do Combobox).
- **Razão**: nunca teto 0; nunca 500 na criação do evento.

## D15 — Janela de deploy

- **Decisão**: `CalcularOrcamentoResult.quote.produtos` opcional no TS; se há produto selecionado e
  `quote.produtos` veio ausente, "Gerar Orçamento" fica desabilitado com aviso. Chave separada (D1)
  garante que o backend velho não cobra errado — só ignora.

## D16 — Script dos tetos já gravados

- **Decisão**: `specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py` (`scripts/oneoff/` é
  gitignored; molde `specs/239b-hotfix-carrinho-fora-de-sp/reclassificar_fora_de_sp.py`):
  relatório de `EventRole` com `character_name` ∈ {Papai Noel, Ajudante do Noel}, `cache_cap` ∈ {712,
  423} (exato), em eventos a partir de 16/10/2026; `--execute` rebaixa para 600/270 só onde
  `cache_value IS NULL AND talent_id IS NULL`, acrescentando "(teto corrigido pela 309: 712 → 600)" ao
  `cache_cap_note`; as demais ficam listadas como "conferir à mão". Roda com `MANTO_SEM_THREADS=1`.
- **Razão**: vínculo 273 nunca rebaixa (`orcamento_evento_ops.py:701-704`); sem o script os eventos
  de dezembro ficam com 712 até alguém editar.

## D17 — `verify_307.py` reescrito

- **Decisão**: cenários que afirmam 712/2.501/3.601/teto 712 passam a 600/2.210/2.912/teto 600; a
  config de teste da 307 grava Noel `[600, …]` e passa a afirmar que a carga NÃO troca para 712; a
  faixa natal (5.010/7.181 para avulsos) continua. A mudança de regra fica registrada no `docs/03`.
- **Razão**: a 307 é regressão obrigatória da 309 e o comportamento mudou por decisão do dono.

## D18 — Telas

- **Calculadora**: card "Produtos de tabela" no topo da coluna direita (antes de Equipe,
  `OrcamentoCalculadoraPage.tsx:616`): `Combobox` (clearable, `fallbackIcon`) com os produtos `ativo` de
  `opcoes.data.settings.produtos ?? {}` (description = preço normal), lista de selecionados com
  `AnimatePresence` (rótulo, chip "preço de tabela"/"estimativa", vagas incluídas, Remover); estado
  `produtos` em `INITIAL_STATE` (:62-84), `useState` (:179-199), `resetAll` (:273-298), payload
  (:303-357) e rehydrate (:245-271); `coordenadoresInclusos` para o `PerformersEditor` (prop opcional);
  avisos de `quote.avisos`; valor único quando as 4 colunas são iguais e só há produto; botão travado
  (D15).
- **Resultado** (`OrcamentoResultadoPage.tsx:229-233`): linha "📦 <rótulo> — preço de tabela R$ X"
  (ou "estimativa") junto das notas.
- **Configuração** (`OrcamentoConfigPrecosPage.tsx:463-478`): `ProdutosConfigCard` no molde do
  `DatasEspeciaisCard` (props `{chave, produto, faixas, erros, onChange}`, erro por campo com foco):
  rótulo, descrição, ativo, preço (`MoneyInput`), uma linha de preço por faixa existente, vagas como
  chips (+ tipo + label + cachê "pela tabela"/valor), `inclui_noturno`; bloco `produtos_estimativa`
  (fator e markup) num card pequeno; rodapé filtra `produtos.*`; "Remover" produto = `null` na chave.
- **Razão**: `PriceTable` não se aplica (preço escalar); nada de `<select>`.

## D19 — Visibilidade dos cachês

- **Decisão**: `GET /opcoes` já entrega `settings` inteiro a todo COMERCIAL (`orcamento_read.py:55-71`);
  `produtos` vai junto. Registrado no `docs/05` como dívida leve; recorte só-superadmin é fatia própria.

## D20 — Esforço e fatias

- **Decisão**: 6–7 noites — N1 spec/clarify/plan/checklist/tasks + `verify_309.py` vermelho; N2–N3
  núcleo (`produtos.py`, settings, quote_ops, pdf, write, educa) até cenários de venda e migração
  verdes; N4 teto/vagas + prefill/`_total_da_duracao` + script até cenários 8–10 e 18 verdes; N5–N6
  telas (card da calculadora, card de configuração, resultado, rehydrate, botão) + conferência no
  Browser pane; N7 `verify_307` reescrito, regressão, converge, docs.
- **Razão**: os céticos derrubaram as 5 noites dos arquitetos (verify com criação de evento e
  `assign_role` por papel; card de configuração aninhado maior que o da 307).
