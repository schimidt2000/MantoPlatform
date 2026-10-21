# Reconferência do plano 3b (noite do desconto) contra a `main` de 21/10 (`c074657b`)

Três leitores só de leitura, em paralelo (núcleo; endpoints/prefill/proposta; tela), conferindo o plano
`docs/backlog/3b-calculadora-desconto-e-dias.md` (escrito em 01–02/10 contra `f6ad283`) contra o HEAD. Desde o
plano entraram 305 (BV do orçamento no evento), 307 (Noel em data especial), 309 (produtos de tabela), 299/299b,
306/312. **Vale esta reconferência onde ela diverge do plano.** Linhas conferidas com `git show HEAD:`.

## 1. Núcleo — `app/orcamento/quote_ops.py`

- `calculate_quote` em `:106-751` (~645 linhas; o plano dizia `:58`, 500). Ordem da conta, sem desconto em lugar
  nenhum: cachês e coordenador `:224-312` → markup `:326-333` → **produtos 309 `:338-342`** → brinde `:344-347` →
  noturno `:349-359` → técnico `:361-366` → maquiador `:368-382` → transporte especial/BGE `:384-407` → fora de SP
  `:409-441` → acréscimos `:443-472` → nota (`NF_DIVISOR`) `:474-480` → extra `:482-488` → personalizado `:493-534`
  → TOTAL `:536`. Os % de acréscimo incidem todos sobre o mesmo `t` (`:466-471`): o BV não vê o "Outro".
- **A função única do passo 6a já existe** (305): `bv_que_acompanha(bv, venda, total)` em `:59-86` (Decimal
  HALF_UP, tolerância de R$ 0,01). Quatro chamadores: `orcamento_evento_ops.py:427-436`, `cancel_ops.py:220-230`,
  `comercial_ops.py:739-765` (B10), `comissoes_ops.py:1087-1097`. **Não mudar assinatura nem tolerância.**
- `valores_brl` por acréscimo existe (`:452-466`); BV em reais grava `[v,v,v,v]` (`:463`); personalizado zera
  (`:503-505`).
- PIX: 5% fixo, dois `0.95` soltos — mensagem `:605-613` (frase `:650`) e PDF `pdf.py:234-242`; não gravado em
  chave. `AVISTA_FATOR = 0.95` já existe em `app/educamanto/pricing_ops.py:29` (candidata à constante única).
- Duração extra: sem produto `totals[3]/4*h` (`:488`); com produto `produtos.total_na_duracao` (`:486`,
  `produtos.py:283-292`) — produto fixo, o resto escala (acréscimos em R$ inclusive). `parte_do_produto_no_total`
  (`produtos.py:269-280`) supõe `(1+Σ%)÷0,84`.
- Quebra "total − transporte" em `_dur_block` `:555-562` (`:558`), sobre o valor final.
- Mensagem: três formatos desde a 309 (`:577-613`): durações; produto + avulsos (`bloco_da_mensagem` com o preço
  cheio do produto, `produtos.py:351-358`); só produto (um valor, "Total da visita" só quando ≠ produto, PIX sem
  rótulo `:606-607`). Nota da data especial (307) depois do deslocamento (`:625-631`).
- Snapshot `:715-749` (sem `incluir_duracao`: dívida 105); `save_quote_history` `:754`, `legacy_quote` `:774`,
  `quote_for_entry` `:819`. Chamadores de `calculate_quote`: `/calcular` (`orcamento_write.py:51`) e EducaManto
  (`app/educamanto/quote_ops.py:143`, `pop` de `event_date`/`produtos` em `:124-129` — é ali que entram os de
  desconto).

## 2. O evento — a 305 fixou o denominador e a régua acima de 4h

- `_total_da_duracao` (`app/calendar/orcamento_evento_ops.py:165-191`) lê `entry.total_Nh` e alimenta
  `acrescimos_do_orcamento` (`:303`, `:307`), `deduzir_duracao` (`:347-369`), `bv_nasce_no_vinculo` (`:462`) e o
  teto de `_valor_gravado` (`:216`). **Depois da P1, `total_Nh` tem desconto: venda ÷ total dá 1 e o BV não
  encolhe; `deduzir_duracao` compara o `sale_value_gross` (cheio) com o total com desconto e não acha a duração.**
  Correção: o cheio no denominador (com reserva no `total_Nh` legado). Os helpers leem o `form_snapshot`
  (`snapshot_do_orcamento`, `:65-72`): o cheio e a base de 4h precisam estar onde eles leem.
- Acima de 4h, quatro réguas velhas: `acrescimos_do_orcamento` com `fator = h/4` em toda linha, R$ e BV em reais
  inclusive (`:312`, `:328`); `_linhas_na_duracao` "fixa × h/4" (`:276-279`); `produtos.total_na_duracao` e
  `base_na_duracao`; o prefill (`routes.py:3383-3391`). **A Q7/Q9 manda o R$ entrar uma vez: precisa de uma marca
  de regra no orçamento salvo** — o novo pela regra nova, o salvo pela velha. `verify_305` cen_04 (BV de 375 em 6h,
  orçamento sem a chave) tem de continuar verde.
- `_valor_gravado` exige `len(valores_brl) == 4` (`:216-230`): a extra precisa de chave própria, não de um 5º valor.
- `plano_dos_acrescimos` (`:383-442`): proporção entre líquidos (× 0,84 com nota). `gravar_acrescimos_do_orcamento`
  (`:492-564`) substituiu `_criar_acrescimos_do_orcamento`. Alerta `bv_do_orcamento_pendente` (`:605-649`).
- Vínculo 273: `aplicar_valores_do_orcamento` `:864-916` grava `sale_value = sale_value_gross = total` (`:904-905`),
  só 1h–4h (`:893-897`), só evento sem venda (o R$ 0,01 da 299 conta como sem venda); recusa cancelado
  (`agenda_write.py:1708-1713`, núcleo `:1035-1038`); exige o PIX do BV.
- Prefill: `_build_orcamento_prefill` em `app/calendar/routes.py:3322-3416` (endpoint `app/api/agenda.py:188-200`);
  manda `total_1h..4h`, `total_custom` (re-derivado `:3375-3392`), `acrescimos_do_orcamento` (305, `:3416-3450`,
  `valores_brl` = BV cheio). O PIX de quem recebe o BV vai no corpo do `POST /api/events` (`agenda_write.py:1160-1190`).
- Gêmeo Jinja: a B8 da 305 recusa criar evento de orçamento com BV (`routes.py:4266-4283`).
- 306/312: o corte de um dia redimensiona o bruto (`cancel_ops.py:1315-1338`, `:1922-1924`); a passagem ao novo 1º
  dia leva bruto e orçamento (`group_ops.py:82`).

## 3. Tela

- `OrcamentoCalculadoraPage.tsx` (904 linhas): debounce 400 ms `:45`, efeito `:369-392`, `calcPendente` + `seq`
  (307) `:208-213`, `:376-386`; card Resultado `:831-887` (rótulo "Preço de tabela" com `valor_unico` `:839`,
  data especial `:853-857`, produto `:859-870`); "Ajustes Finos" `:707-820`; ajuda da duração extra `:720-730`
  (a frase que mente em `:729`); "Recalcular" `:249-278` (restaura `produtos` `:255`); 23 `useState` `:183-204`,
  `INITIAL_STATE` `:64-88`, `resetAll` `:280-306`; erros de campo soltos no fim de Ajustes `:825-829`; card opaco só
  com `calcular.isPending` (`:837`).
- Tipos `lib/orcamento.ts`: Input `:169-202`, `Quote` `:230-280`, FormSnapshot `:455-484`, MemoriaLinha `:223-228`,
  `OrcamentoHistoricoEntry` `:396-413`. `MemoriaDeCalculo.tsx`: seis tipos (+ `produto`) com fallback.
- `AcrescimosEditor.tsx`: linha nova nasce com `tipos[0]`, o BV é o último da lista
  (`OrcamentoCalculadoraPage.tsx:702`, `EducaMantoCalculadoraPage.tsx:891`) — "linha nova cujo tipo é BV" só
  acontece na troca de tipo; o editor não sabe qual tipo é BV (prop nova). A frase "acompanha o desconto" não vale
  no EducaManto (`EducaMantoCalculadoraPage.tsx:886`): ligada por prop.
- `OrcamentoResultadoPage.tsx`: durações `:37-57`, mensagem `:211`, "Criar evento" `:204-206`, transporte
  `:261-292`, memória `:294-310`. `OrcamentoHistoricoPage.tsx:275` (selo), totais `:277-281`.
- `EventCreatePage.tsx`: prefill grava bruto = venda `:212-213`, `selectDuracao` `:286-293`, `selectDuracaoExtra`
  `:301-314` (régua linear no navegador, já errada com produto), "Outra (h)" `:750-801` (preço `:779-796`);
  `BvDoOrcamentoBlock.tsx:60-90` (BV cheio "no total de R$ X" `:87`; aviso "valor diferente" `:73-79`, `:90-95`),
  montado em `EventCreatePage.tsx:818-842` com `totalDaDuracao = total_Xh`.
- `ValoresBlock.tsx`: campos `:138-185`, conta `:74`, selo `:186-190` (`toFixed(1)`: ponto e meio para cima — a
  proposta é para baixo, com vírgula). `ComercialSection.tsx:999`, `:1060-1063`.

## 4. Riscos que o plano não conhecia

1. O BV do evento não encolheria (seção 2) — FR-023.
2. Quatro réguas acima de 4h e a marca de regra no orçamento salvo — FR-008.
3. Três formatos de mensagem (309) e o PDF de uma página que já aperta (307) — FR-015.
4. Desconto sobre o preço de tabela (Session 1 da spec).
5. Bilateral e debounce: só o campo do modo ativo vai no payload; o outro vem do resultado; um laço se o resultado
   alimentar o estado do payload; "2" com pausa = 99,9% por um instante — FR-016/FR-017.
6. Card desatualizado no erro/debounce — FR-017.
7. "Recalcular" de snapshot antigo tem de zerar o desconto explicitamente — FR-020.
8. Dois arredondamentos para o mesmo desconto (selo × proposta) — FR-022.
9. Acréscimo negativo aceito pelo servidor (dívida 100) — Session 2.
10. Paridade: gabarito na `c074657b` com a tabela atual (a 309 migrou Noel 712→600; a faixa 24/25 sai da data); o
    `verify_309_golden.json` é molde, não oráculo; exceções novas: produto acima de 4h com R$ e produto com BV +
    outro acréscimo.
11. Arredondamento: totais em `round()` de float; 305/309 em Decimal HALF_UP — sem desconto o PIX tem de ficar igual
    byte a byte.
12. A extração do `_calcular_dia` (Preparação) pertence à noite dos dias; aqui só o que a P1 precisa (`faixa` 307 é do
    dia; `produtos` e `split_coordenadores`, a decidir quando os dias vierem).

## 5. Já feito ou caiu

- A 3a é a 305, em produção desde 15/10: "sobe junto com a 3a" e o verify cruzado viram regressão
  (`verify_305 --regressao`).
- O BV gravado no evento pela venda salva, o B10 (acompanhar a venda editada) e o `acrescimos: []` do Novo evento
  (o servidor cria os acréscimos) — feitos pela 305.
- Premissa 36 (devolução ≠ desconto): a 306 já redimensiona o bruto.

## 6. Recontagem em produção (21/10, só leitura)

2.710 orçamentos (226 em outubro); desde junho, 267 vendas com valor, 92 com desconto (63 na faixa de ~5%, 19 entre
5 e 10%, 5 acima de 10%, 5 abaixo de 4,9%); das 91 vindas de orçamento, 89 com o "antes do desconto" igual a um
total do orçamento; acréscimos: 187 "Outro" em R$, 41 "Outro" em %, 34 BV em %, 25 Deslocamento em R$, 2 urgência,
2 BV em reais, nenhum negativo; 121 orçamentos acima de 4h, 11 com acréscimo em R$, nenhum com produto; nenhum
orçamento com produto de tabela; 12 eventos de orçamento desde a 305, nenhum com BV.
