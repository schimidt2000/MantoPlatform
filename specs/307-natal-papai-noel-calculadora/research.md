# Pesquisa — feature 307 (Phase 0)

Sem `NEEDS CLARIFICATION` na spec. Este arquivo registra as decisões técnicas com razão e
alternativas, para o `/speckit-analyze` e o converge não as reabrirem. Fontes: leitura do código na
`main` d855d1a, espelho `manto_local` de 30/09/2026 (consulta só leitura), planilha
`Logistica Natal 2025.xlsx`, dois refutadores do workflow `wf_b6bb9966-f58`.

## D1 — Gatilho pela data do evento, não seletor manual

- **Decisão**: a faixa é resolvida no servidor a partir de `payload["event_date"]`
  (`"AAAA-MM-DD"` → `"MM-DD"` ∈ `faixa.dias`), sem estado novo no React.
- **Razão**: pedido literal do dono ("quando a data selecionada for essa, o cálculo é feito
  diferente"). O seletor manual (padrão da 262) depende de a comercial lembrar — que é exatamente o
  defeito do acréscimo "Outro" de hoje (24 de 37 orçamentos com Noel).
- **Alternativas**: seletor manual com alertas (proposta do arquiteto do workflow) — rejeitada pelo
  dono; automática com override — desnecessária (o personalizado já é o override de preço).
- **Consequências**: a data é opcional; sem data, preço normal. A calculadora mostra dica com a data
  vazia e aviso com a data na faixa. EducaManto manda `event_date` e precisa removê-lo
  (`educamanto/quote_ops.py:121-123`).

## D2 — Um bloco `datas_especiais` na tabela, com faixa `natal` padrão

- **Decisão**: `pricing_config["datas_especiais"] = {"natal": {rotulo, dias, markup[4],
  cache{especial: [4]}, coordenador[4], piso[4], nota_mensagem}}`; `_migrate` faz `setdefault`.
- **Razão**: é "a tabela de valores que já tem no sistema" (o dono); segue o padrão dos blocos
  `transporte`/`educamanto_som_luz` (feature 235) — sem migration, editável pelo superadmin.
- **Alternativas**: `markup["natal"]` (exigiria mexer em `_inject_3h`, no save e no tipo TS do
  markup só para uma lista); especiais duplicados "Papai Noel 24-25/12" (inflaria cachê e venda pelo
  mesmo markup 2,6 e viraria teto de ~1.673).

## D3 — Markup 3,34 com cachês reais; piso para os demais; coordenador da faixa com e sem show

- **Decisão**: markup `[3.34, 3.34, 3.34, 3.34]`; `cache` = Papai Noel `[1000, 2000, 3000, 4000]`,
  Ajudante do Noel `[650, 1300, 1950, 2600]`; `coordenador` `[500, 1000, 1500, 2000]` (uma lista,
  vale com e sem show); `piso` `[650, 1300, 1950, 2600]` aplicado a qualquer performer sem
  sobrescrita: `max(tabela, piso)`.
- **Razão**: cachês reais da planilha (Noel 850–1.000, ajudante 650, coordenador 500/casa); o dono
  escolheu 3,34 (Noel ≈ 5.010 / Noel + 1 ≈ 7.181). O piso vem do refutador: sem ele, Noel + boneco
  (200) sairia a 5.678 — mais barato que Noel + ajudante — e o teto do boneco ficaria em 200 contra
  500–750 pagos em 2025. Cachês lineares por hora: com progressão normal, 4h de Noel sairiam por
  +17 % sobre 1h na noite em que o tempo do Noel é o recurso escasso.
- **Alternativas**: markup por papel (3,33× Noel / 2,31× ajudante) — muda o invariante "um markup
  por orçamento", segunda fatia; "taxa da data" fixa em R$ pós-markup (bate 5.000/6.500 exatos com
  markup 2,31) — não é "markup", fica como opção futura; markup 3,0 (4.500/6.450) — o dono preferiu
  não baixar o Noel.

## D4 — Faixa normal: Papai Noel 712 e "Ajudante do Noel" 423 por migração guardada

- **Decisão**: DEFAULTS ganham os dois especiais; `_migrate` injeta "Ajudante do Noel" (regra
  existente para especiais ausentes, respeitando `especiais_excluidos`) e troca "Papai Noel"
  **somente se** estiver exatamente em `[600, 650, 675, 700]`.
- **Razão**: com o markup real 2,6 e coordenador 250, 712 → R$ 2.501,20 e 423 → +R$ 1.099,80
  (tabela 2.500/3.600, escolha do dono). O guarda pelo valor exato é o padrão "Transformer → BGE":
  valor editado pelo time nunca é tocado. Sem isso a tabela normal exigiria edição manual no deploy.
- **Alternativas**: script de dados no Shell do Render (um passo manual a mais, "para ontem" não
  comporta); só DEFAULTS (não vale: "Papai Noel" já existe na config salva, DEFAULTS não sobrepõem).

## D5 — `_migrate` defensivo

- **Decisão**: o passo 307 em `_migrate` nunca indexa sem `isinstance`; bloco ou faixa malformados
  (`None`, lista, faixa sem `dias`, markup com 3 valores) são substituídos/normalizados pelo padrão.
- **Razão** (refutador de código): `_migrate` roda dentro do `try` de `load()`; qualquer exceção
  devolve `deepcopy(DEFAULTS)` para a tabela inteira — markup 3,0 no lugar de 2,6 e sem "Papai
  Noel", o que faz todo orçamento com Noel levantar `QuoteValidationError`. Cenário 12 do verify
  cobre `datas_especiais` nulo e malformado.

## D6 — Teto das vagas pela data do evento (criação e vínculo) e pela data do orçamento (prefill)

- **Decisão**: `_compute_performer_caches(snapshot, horas_extra=None, data_evento=None)`; a criação
  passa a data do evento sendo criado, o vínculo 273 passa `event.start_at.date().isoformat()`, o
  prefill usa `snapshot["event_date"]`.
- **Razão**: o artista é pago pelo dia em que trabalha; a 273 permite vincular um orçamento de 20/12
  a um evento de 24/12. O prefill só conhece o snapshot.
- **Alternativas**: sempre a data do snapshot (teto errado no vínculo com data diferente); gravar a
  faixa no snapshot (o 3b vai reescrever o snapshot; evitar chave nova sem necessidade).

## D7 — "Gerar Orçamento" travado enquanto há recálculo pendente

- **Decisão**: estado `calcPendente` ligado no início do efeito que agenda o recálculo e desligado no
  `onSettled`, com um contador `seq` (ref) que descarta `onSuccess`/`onSettled` de um cálculo que não
  é mais o atual; `disabled={saved || calcPendente || calcular.isPending || calcular.isError}` e o
  texto "Recalculando…".
- **Razão** (refutador + analyze): `calcular.isPending` só liga depois dos 400 ms de debounce; no
  intervalo o botão salva o `result` anterior e o `/salvar` grava sem recalcular — trocar a data
  para 24/12 e clicar rápido gravaria o preço comum. E no TanStack v5 os callbacks valem para a
  mutation mais recente do observer: uma resposta antiga em voo poderia destravar o botão com o
  resultado velho — daí o `seq`.
- **Aviso dourado**: lê `quote.data_especial` do próprio resultado (fonte: servidor) — o React não
  reimplementa o recorte `MM-DD` (Princípio I); só a dica com a data vazia lê os dias da tabela.

## D8 — Memória, mensagem e PDF

- **Decisão**: sem tipo de linha novo (`MemoriaLinha.tipo` é união fechada): a linha "× Markup"
  ganha `detalhe` "Véspera e Natal (24/12)"; cachês sobrescritos ganham "cachê de Natal" e os
  elevados ao piso "piso de Natal" nas `partes`; `quote["data_especial"] = {chave, rotulo, markup}`;
  nota em itálico após a `deslocamento_nota` na mensagem e após a frase de deslocamento no PDF.
- **Razão**: hotfix 210 exige que a memória some com o total; o PDF re-deriva texto (não usa
  `message`) — as duas superfícies andam juntas (lição da 262).

## D9 — Validação do bloco no `POST /settings`

- **Decisão**: a validação mora no núcleo — `settings.validar_datas_especiais(bloco, especiais)`
  levanta `SettingsValidationError(message, fields)` (padrão de `QuoteValidationError`); o endpoint
  só traduz em `json_error("Datas especiais inválidas.", 400, fields=exc.fields)`. Regras: chave
  `^[a-z0-9_]{1,30}$`; `dias` `MM-DD` reais, sem repetição, vazio = desligada; `markup` 4 valores em
  `[1.0, 6.0]` gravados com 2 casas HALF_UP; `cache`/`coordenador`/`piso` 4 valores ≥ 0 via
  `parse_brl` (string inválida ou negativo é ERRO, não default); `cache` só para nomes em
  `especiais`; `nota_mensagem` ≤ 200 chars. Excluir um especial limpa a sobrescrita dele das faixas.
- **Razão**: o save atual converte markup com `float()` sem limite; 33,4 no lugar de 3,34
  multiplicaria o Natal por 10 ao vivo (refutador). Regra de negócio no endpoint feriria o
  Princípio III (analyze).

## D10 — Fora de escopo confirmado

Loja virtual (304); pacote de 30 min com preço fechado; markup por item; cachê por região fora de
SP; alerta "já na agenda" por talento; bloqueio de boneco/show; costura do 3b (`docs/backlog/` não
existe na `main` — fica para a 306).
