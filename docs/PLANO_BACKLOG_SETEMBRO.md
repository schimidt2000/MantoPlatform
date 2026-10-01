# Plano — backlog do sistema de setembro/2026

**Data**: 2026-09-23, atualizado em 2026-09-29 · **Origem**: notas do Google Keep do dono,
triadas em 22–23/09 · **Estado**: decisões D1–D36 tomadas; onda 1 iniciada em 29/09; em 30/09 a 303 foi dividida em três entregas
e o plano da primeira ficou pronto.

O dono quer fechar esta lista o quanto antes para começar outro projeto grande, **sem sair da
esteira**. Este documento existe para que cada `/speckit-specify` já nasça com as decisões dele e
o `/speckit-clarify` de cada feature tenha pouco a perguntar. Os nomes das features são
provisórios: o número nasce em `specs/` (constituição VI). A décima nota, "Horário final do evento
no portal e mais detalhes", já foi entregue — é a feature 302.

## Como a triagem foi feita

Nove batedores de leitura (um por nota) mapearam código e `manto_local`; nove revisores tentaram
refutar cada mapa; uma síntese juntou tudo. As afirmações que decidem escopo foram conferidas de
novo à mão contra o código (seção "Fatos conferidos"). **O espelho é velho** — agenda até 03/09,
`audit_logs` até 15/09, orçamentos até 26/08, gastos até 13/08, formulários até 12/08: toda
contagem que decide escopo se reconta em produção, só leitura, antes do specify da feature.

## Fatos conferidos que mudam a prioridade

1. **O sync do Google apaga evento com dinheiro.** O fluxo "Solicitar exclusão" (224) tem zero
   uso; a equipe cancela apagando no Google, e `_cleanup_stale_events`
   (`app/calendar/routes.py:341`) apaga do banco sem consultar venda nem comprovante — só a venda
   virtual é poupada (`virtual_divergente`, mesmo arquivo, ~`:371`). No espelho: 8 apagões em
   agosto e 2 até 15/09; 31 eventos futuros com R$ 108.520,51 em comprovantes anexados expostos
   (163 eventos e R$ 997.929,49 contando todos os meses). A dívida 49 já registrava o caso do
   grupo. **Até a trava existir, a equipe não apaga no Google evento com venda.**
2. **O BV do orçamento não chega ao evento.** O Novo evento envia `acrescimos: []` fixo
   (`frontend/apps/internal/src/pages/EventCreatePage.tsx:432`). A Planilha já lista todo BV de
   evento (`app/api/financeiro_read.py:706`) — a metade "cai na planilha" da nota já existe. E a
   cópia calcula o % sobre `event.sale_value` (`app/calendar/routes.py:3301-3310`), que já inclui
   o próprio BV e a nota fiscal: contra a regra da 099.
3. **O estorno de comissão já paga não é descontado de ninguém.** `aplicar_estorno_comissao`
   copia `sale_date` e `payable_from` da venda antiga (`app/calendar/cancel_ops.py:148-149`); a
   Planilha monta a comissão pelo ciclo do mês (`app/financeiro/routes.py:904`,
   `_build_commission_items`), então o estorno cai num mês já pago. A docstring
   (`cancel_ops.py:135-137`) promete o contrário e cita `_seller_payable_rows`, que é da tela de
   Comissões, não da Planilha.
4. **O BV de evento cancelado continua na Planilha**: a consulta de `financeiro_read.py:706` não
   filtra `cancelled_at`.
5. **O formulário perde a idade e o nome do aniversariante** em parte das respostas:
   `app/formularios/pre_evento_ops.py:42-43` não conhece as chaves do WhatsForm
   `idade_a_completar_do_aniversariante` e `qual_o_nome_do_a_aniversariante` (a triagem mediu 720
   e 360 respostas no espelho).
6. **Recados da luminária somem depois de lidos.** O único acesso é o selo de não lidos
   (`frontend/apps/internal/src/components/nfc/NfcVideoCard.tsx:102`), e abrir marca tudo como
   lido; tag sem vídeo nem tem card (`NfcVideoCard.tsx:40-41`) — quebra o SC-008 da 297.
7. **O evento só é EducaManto pelo prefixo `(EDU` no título**, e `build_gc_title`
   (`app/calendar/event_ops.py:385`) troca o prefixo sem aviso quando se escolhe outro tipo — a
   comissão EDU depende disso.

## Recontagem em produção (29/09, só leitura)

Feita antes de iniciar a onda 1, porque o espelho estava velho. Corrige a triagem em três pontos:

- **Sync**: 5 eventos apagados por sumiço no Google desde 01/08 (2 em agosto, 3 em setembro). Em
  17/09 foi o `(R&I) GABBY + PANDY + GATUNO` (1244), com venda e comissão de R$ 92,39: movido no
  Google de 13 para 19/09 e depois tirado de lá; recriado pela comercial em 24/09 como evento novo
  (1336, 07/11). Hoje são **56 eventos futuros com R$ 172.447,24 em comprovantes** (no espelho, 31
  e R$ 108 mil). "Solicitar exclusão" e "Cancelar" têm **zero** uso.
- **298b**: dos 202 formulários desde 01/06, perdem-se de verdade só
  `idade_a_completar_do_aniversariante` (70) e
  `gostaria_que_a_confirmacao_do_evento_seja_com_assessoria_se_sim_digite_o_telefone` (36).
  `qual_o_nome_do_a_aniversariante` tem **zero** ocorrências em produção — o nome chega como
  `nome_do_aniversariante`, que já é conhecido. As outras chaves desconhecidas são de contato (vêm
  das colunas da resposta) ou o endereço da contratante (excluído de propósito).
- **EducaManto**: o tipo gravado é `EDUCAMANTO` (não `EDU`). Os 4 eventos EDU vieram todos do
  Google, e mal: no Jundiaí (1321–1323) o nome do musical virou uma vaga de elenco, não há técnico
  de som e os ensaios 1247/1248 não estão ligados ao evento.
- **224g**: o estorno 211 (−R$ 92,39) nasceu em 17/09 com a data de venda de 21/08 — o fato 3
  confirmado em produção. **D16**: o estorno de −R$ 114,14 não existe mais em produção; resta
  conferir o de −R$ 170,00.

## Decisões do dono (22–23/09, não reabrir)

| # | Tema | Decisão |
|---|---|---|
| D1 | Cancelamento | Passa pelo sistema **de verdade**: evento com venda ou comprovante que some do Google vira pedido para o dono decidir, em vez de ser apagado; "Solicitar cancelamento" com aviso no sino. |
| D2 | Base do BV | O BV é o valor em R$ que o orçamento **somou ao preço** — 10% do preço antes do BV e da nota. Ex.: show de R$ 1.000 com BV de 10% e nota → cliente paga R$ 1.309,52, quem indicou recebe **R$ 100,00** (hoje o evento gravaria R$ 130,95). |
| D3 | Desconto | % na calculadora, salvo no orçamento, mostrado na mensagem e no PDF, e levado ao evento como "valor antes do desconto" e "valor de venda". |
| D4 | PIX à vista | Não soma com o desconto negociado: **vale o maior**. |
| D5 | Dias adicionais | **Agora.** Cada dia adicional nasce igual ao primeiro e pode ser personalizado (personagens, duração, horário, transporte sim/não). A venda fica no 1º dia; os outros dias entram no grupo comercial (feature 055) sem valor. |
| D6 | Luminária | **Recados e vários vídeos, agora.** A página pública ganha um menu "Recados especiais" com a lista de vídeos, cada um com o seu título. |
| D7 | EducaManto | Só o tipo EDU no Novo evento e na edição; Comercial e Superadmin lançam. Sem permissão nova. |
| D8 | Marketing | Três peças: (1) canal "Como você conheceu a Manto?" no orçamento, levado ao evento, e a mesma pergunta no formulário de pré-contrato; (2) canal no Gasto Extra de marketing; (3) a tela Desempenho mostra gasto, orçamentos, eventos, faturamento e custo por cliente por canal, com o **BV como custo do canal parceiro**. O Kommo segue em uso, sem origem. |
| D9 | Lista de canais | Aprovada: Instagram ou Facebook · Google (pesquisa ou anúncio) · Vi um show da Manto em outra festa · Indicação de amigo ou familiar · Indicação do buffet, espaço ou cerimonialista (+ "Quem indicou?") · Já fui cliente da Manto · Site da Manto · Outro (+ "Qual?"). Anúncio e orgânico juntos de propósito. |
| D10 | Acessórios | **Agora.** A pessoa de Ensaio escreve a ficha de acessórios do show; o Figurino vê; a ficha sai na impressão com prioridade, antes das fichas de figurino — como a ficha manual de hoje. |
| D11 | Aniversariantes: quem vê | Equipe interna e elenco que **aceitou** o evento. O convite não muda. |
| D12 | Aniversariantes: fonte | Vem do formulário, mas **exige a conferência da comercial** antes de ir ao portal. |
| D13 | Coordenador | Lista de afazeres padrão, personalizável por evento; o coordenador abre o portal e vai marcando. |
| D14 | Comissão sobre o retido | **Sim.** Mesmo % do vendedor sobre (pago − devolvido). Ex.: venda R$ 2.000 a 5%, sinal R$ 1.000, devolvidos R$ 600 → retido R$ 400, comissão R$ 20; se os R$ 100 cheios já foram pagos, o próximo repasse desconta R$ 80. Muda a regra de `comissoes_ops.py` (~`:826`: cancelado nunca comissiona). |
| D15 | BV do passado | Script mostra a lista, o dono aprova; modo de teste primeiro, depois o dono roda no Shell do Render. |
| D16 | Estornos existentes | O financeiro confere. O de −R$ 114,14 (parado em junho) vai ao próximo dia 5; o de −R$ 170,00 (pago em 10/08) só entra se o financeiro confirmar que não foi descontado. *(29/09: o de −R$ 114,14 não existe mais em produção.)* |
| D17 | Trava mínima do sync (29/09) | **Entra na onda 1**, separada do cancelamento completo: o sync para de apagar evento que não esteja vazio (a regra `pode_excluir` da 224). |
| D18 | Evento com venda que some do Google (29/09) | **Fica e avisa no sino**: continua na agenda, marcado, e segue contando na venda; o Superadmin é avisado e decide (volta ao Google ou cancela pelo sistema). Se o evento só mudou de mês, a marca some sozinha quando o sync o acha na data nova. |
| D19 | EducaManto (29/09) | **Tipo + equipe do musical**: o evento nasce com as vagas por função (cara limpa, bonecos, produção, técnico) do orçamento EducaManto. **Substitui a D7**; vira Nível 1 e sai da onda 1. |
| D21 | Aviso do sumiço (29/09) | "Não deve ser apenas um aviso no sino": **faixa fixa no topo de todas as telas + sino**, para **Superadmin e Comercial**; a decisão é só do Superadmin. |
| D22 | Devolução (29/09) | "Muitas vezes precisamos devolver o dinheiro" — entra na 303: cancelar com devolução total, parcial ou nenhuma, e o evento mostra devolvido, retido e o estado do pagamento. |
| D23 | Comissão sobre o retido (29/09) | A D14 entra na 303, junto da devolução; a correção 224g (estorno no ciclo certo, BV de cancelado fora da Planilha) vai junto, porque é a mesma função. |
| D24 | Portal durante a espera (29/09) | O elenco vê o evento com "Evento em confirmação — entre em contato com a produção" — complemento da mensagem que a produção já manda no WhatsApp. |
| D25–D29 | Clarify da 303 (29/09) | Comissão do cancelado proporcional ao retido; BV negociado caso a caso; devolução vem vazia (Tudo/Parte/Nada); devolução alterável na tela do evento com a comissão acompanhando; técnico de som automático não conta como escalado no sync. Fonte: `specs/303-sync-nao-apaga-venda/spec.md` §Clarifications. *(Resolvido nas D30–D33.)* |
| D30–D33 | Cancelado nos relatórios (29/09) | "Evento cancelado com 600 devolvido aparecendo como −600, sendo que ele é +400": o retido entra na DRE no **mês do cancelamento**; **card + botão "Mostrar cancelados"** para sinalizar e filtrar; imposto sobre o retido **depende da negociação** (informado no cancelamento); o **retido conta como venda** do vendedor no mês do cancelamento. Fonte: spec 303 §Clarifications. |
| D34 | Divisão da 303 (30/09) | **Três entregas**, cada uma com número, esteira e deploy próprios: (1) a trava do sync, sem dinheiro; (2) o dinheiro do cancelamento; (3) sinalizar e filtrar cancelados. Motivo: tudo junto eram umas quinze telas num deploy sem ambiente de teste, e reverter um defeito de comissão desfaria a trava. |
| D35 | Intervalo entre a 1ª e a 2ª entrega (30/09) | O evento marcado **só oferece "Devolver ao Google"**; não pode ser cancelado nem excluído até a 2ª entrega. Nenhum cancelamento sai com a regra velha. |
| D36 | Correção depois de cancelado (30/09) | **Sim, só o Superadmin**: acrescentar comprovante esquecido e corrigir BV negociado, com retido e comissão recalculados. Entra na 2ª entrega. |
| D20 | "Pago" sem prova de saída no Gasto Extra (29/09) | **Não agora.** Caso 1246 (Merida + Cavalo): três gastos marcados "Pago" à mão, com um PIX de entrada anexado como "Nota Fiscal". Vai como dívida no `docs/05`. |

**Premissas minhas** (o dono pode corrigir no clarify da feature):
- D5: o que é do pedido, e não do dia, entra uma vez — BV em R$ e taxa de urgência; a nota
  incide sobre a soma (como o EducaManto, FR-016). Hoje a "Duração extra" multiplica tudo em
  linha reta, inclusive o BV fixo.
- D6: até 3 vídeos por luminária (a conversão é uma fila única na plataforma, com trava de banco);
  título e ordem editáveis sem reenviar o arquivo; o recado continua sendo da luminária, não de
  cada vídeo; só Artista 3D e Superadmin leem recados (como hoje).
- D10: lista de itens sem caixa "Separado" por item (a que já existe no figurino foi marcada em 4
  de 46 escalações); sem migration se couber numa Observação rotulada "Acessórios", no padrão do
  aniversariante.
- D12: a falta de conferência aparece como pendência na faixa do evento, como o chip de Logística
  da 302.
- D13: a lista padrão é editada numa tela do ERP pelo Superadmin (o texto deixa de ser caminho
  crítico: a feature sobe vazia e o dono escreve direto no sistema); a produção personaliza a
  lista de um evento e vê o que o coordenador marcou.

## Features e ordem

| Onda | Feature (nome provisório) | Nível | Tamanho | Migration | Notas |
|---|---|---|---|---|---|
| 1a | **303** — sync não apaga evento com venda: marca, faixa + sino, devolver ao Google, aviso no portal | 1 | M–G | sim (1 coluna) | D1 (parte) + D17 + D18 + D21 + D24 + D29 + D34–D35. Não toca dinheiro. Plano pronto em 30/09 (`specs/303-sync-nao-apaga-venda/`); falta a contagem pré-deploy antes do `/speckit-tasks`. |
| 1b | **Dinheiro do cancelamento** (número nasce no specify) — cancelar com devolução, comissão do retido, BV negociado, imposto, correção pelo Superadmin, DRE com o retido, retido como venda | 1 | G | sim (2 tabelas) | D14 + D22–D23 + D25–D28 + D30 + D32–D33 + D36; absorve a 224g. Texto e pesquisa prontos em `specs/303-…/entregas-2-e-3-rascunho.md` e `pesquisa/`. D16 é operação do financeiro, não código. |
| 1c | **Sinalizar e filtrar cancelados** (número nasce no specify) — selo, "Mostrar cancelados", card, página de Cancelamentos para o Financeiro | 1 | M | não | D31. Mesmo rascunho. |
| 1 | Sinônimos do formulário (298b) | 2 | P | não | Fato 5, recontado: duas chaves (idade e assessoria). |
| 2 | Cancelamento pelo sistema (o resto) | 1 | M | a decidir no plan | D1 restante: "Solicitar cancelamento" do Comercial com aviso. |
| 2 | EducaManto: tipo + equipe do musical | 1 | G | a decidir no plan | D19 (substitui a D7), fato 7. Sobe com a onda 2 ou sozinha, o que ficar pronto antes. |
| 3 | BV do orçamento chega ao evento (099b) | 2 | pequeno, mas dinheiro | não | D2 + D15. Mesmo prefill do `EventCreatePage` que o desconto: vai primeiro. |
| 3 | Calculadora: desconto e dias | 1 | G | não (snapshot JSON) | D3 + D4 + D5. `calculate_quote` é compartilhado com o EducaManto: chave nova neutra quando ausente. |
| 4 | Aniversariantes no evento e no portal | 1 | M | a decidir | D11 + D12. Depende da 298b. Nome de criança só depois do aceite. |
| 4 | Checklist do coordenador | 1 | G | sim | D13. Usar `is_event_coordinator` do servidor; não criar a 6ª regra de "quem é coordenador". |
| 4 | Ficha de acessórios do show | 1 | M | provável não | D10. Impressão nova precisa de entrada no `server.js`. |
| 5 | Luminária: recados e vários vídeos | 1 | M | não | D6 + fato 6. Fim da substituição em `add_delivery`; a trava por entrega cobre também o DELETE. |
| 6 | Marketing: canal do cliente | 1 | M | provável sim | D8 (1) + D9. Toca o snapshot do orçamento: depois da onda 3. |
| 6 | Marketing: gasto por canal e Desempenho | 1 | M–G | provável sim | D8 (2) e (3). Relatório de dinheiro com a DRE em duas implementações vivas. |

**Por que essa ordem.** A onda 1 é pequena, quase não depende de decisão e deixa a Planilha
coerente antes das ondas de dinheiro. A trava do sync vem em seguida porque é o único item que
impede uma perda **em curso**. As duas features da onda 3 tocam os mesmos arquivos e sobem juntas,
à noite (a calculadora sangra primeiro), com verify cruzado de comissão, BV e DRE (o BV entra no
CPV). A onda 4 é a operação do evento; a 5 e a 6 não bloqueiam ninguém — e o marketing depende do
snapshot do orçamento da onda 3.

**Tamanho honesto.** Somando, a lista equivale a umas 10 a 12 features do tamanho da 302. Cada
onda é um deploy agrupado, à noite.

## O que é do dono, sem código

- **Agora**: orientar a equipe a não apagar no Google evento com venda — usar "Solicitar
  exclusão" até a trava da onda 2.
- **Agora**: criar a pergunta "Como você conheceu a Manto?" (lista D9) no editor de campos dos
  formulários comum e corporativo. A feature de marketing lê a resposta depois; os dados começam a
  se acumular desde já.
- **Agora**: criar à mão as vagas do Jundiaí (1321) para lançar os cachês — o elenco veio do
  Google como uma vaga só com o nome do musical.
- Caso 1246 (Merida + Cavalo, D20): conferir no extrato de 23–26/09 o que saiu de fato antes de
  corrigir os status; descobrir a que se refere o PIX de R$ 940,00 recebido em 19/09, que não está
  lançado em lugar nenhum.
- Reclassificar o Google Ads de 14/07 (R$ 1.817,91, hoje em "Outros") para "Marketing".
- Financeiro: conferir o estorno de −R$ 170,00 (D16).
- Rodar no Shell do Render os scripts de produção que as features entregarem (retroativo do BV,
  sugestão de aniversariantes nos eventos já agendados): o classificador bloqueia `--execute` por
  SSH.
- Depois da onda 4: escrever a lista padrão do coordenador na tela do ERP.

## Riscos transversais

- **Comissão por quatro portas** (tipo EDU, estorno no ciclo, BV fora da base, desconto e
  retido): cada verify confere a comissão a pagar resultante; as ondas 1–3 pedem um verify cruzado
  da Planilha e da DRE.
- **Gêmeos Jinja** do financeiro (`app/financeiro/routes.py`): filtro de BV cancelado, ciclo do
  estorno e a tela de Comissões têm de ficar iguais nos dois lados, sem "limpar" o Jinja
  (`docs/PARADA_REMOCAO_JINJA.md`).
- **Sync do Google**: a trava mexe em `_cleanup_stale_events`, e qualquer tabela nova ligada ao
  evento entra no caminho de exclusão (CASCADE ou `_clear_event_side_tables`).
- **E-mail real**: aviso ao elenco no cancelamento, `notify_ensaio_team` no EDU com "precisa
  ensaio", convite do coordenador. Verify com `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`.
- **Deploy cruzado**: campo novo no payload do portal, na gestão NFC e no snapshot do orçamento
  nasce opcional no TypeScript e neutro quando ausente.
- **Textos que mentem** e não podem ser copiados para as specs: `cancel_ops.py:135-137`,
  `ExcluirEventoDialog.tsx:69-70`, a ajuda da Duração extra em `OrcamentoCalculadoraPage.tsx`, e
  os trechos de `docs/01`, `docs/02` e `docs/04` sobre "quantidade de aniversariantes" e sobre
  acréscimos apontados pela triagem.
