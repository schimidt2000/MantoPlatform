# Spec 303: síntese da verificação, das lacunas e da pergunta final ao dono

## (a) Correções que a spec precisa (as 8 contestadas, todas confirmadas pela segunda opinião)

**S3. Evento que muda de mês** (spec.md:42-44; cenário 8 do verify, spec.md:417)

Novo texto para 42-44:

> "Há um segundo caminho de perda, menos visível: evento que muda de mês no Google. Em cada mês, a limpeza apaga o evento gravado naquele mês (pela data do banco) que não está na lista do Google. O evento só escapa se algum sync do mês de destino o encontrar antes, pelo id, e gravar a data nova.
> Se foi adiado para um mês posterior, o mês antigo é limpo primeiro e apaga o evento, e o mês novo o importa como evento novo, sem venda, comprovante nem escala.
> Se foi antecipado para um mês já passado, o ciclo automático nunca busca esse mês: o evento é apagado e não volta.
> No 'Limpar eventos fantasma', o antecipado só escapa se o mês de destino já tiver outro evento no banco."

- **Exceções:** venda virtual e evento cancelado. O sync não os atualiza e a limpeza os poupa.
- **Verify:** o cenário 8 ganha a variante "antecipado para mês passado".
- **Evidência:** sync.py:51-53, 66-70, 77-79; routes.py:364-365, 2247, 2294-2295; admin_config_write.py:93-99.

**S4. O que o sync faz com cada item** (FR-002, spec.md:282-285)

Trocar "A regra vale para todo evento, vazio ou não" por:

> "A regra vale para todo evento, vazio ou não, exceto venda virtual e evento cancelado, que o sync não atualiza (ver Casos de borda)."

**S5. Premissa do sync** (spec.md:489-490) e caso de borda (spec.md:253-254)

Nova Premissa:

> "O ciclo automático (thread e sync_worker) sincroniza e limpa do mês corrente até +6 meses, ou até o último evento do banco +1 mês.
> Mês passado só é limpo pelo 'Limpar eventos fantasma' de /admin/sync (Superadmin), que percorre em ordem os meses que têm algum evento no banco.
> 'Sincronizar agora' cobre o mês corrente e os 6 seguintes e não apaga nada.
> O 'Sincronizar' de um evento atualiza só aquele evento, sem limpeza.
> A rota antiga /agenda?force_sync=1 também limpa, mas só responde chamando o backend direto.
> A regra vale em todo caminho que limpa."

- No caso de borda, trocar "(numa sincronização manual de mês antigo)" por "(percebido pelo 'Limpar eventos fantasma')".
- **Evidência:** sync.py:51-64; admin_config_write.py:64-117; routes.py:470-476; frontend/server.js:253-264, 298-302; agenda_write.py:621-636.

**S6. O que é ausência confirmada** (FR-003, spec.md:286-287)

Novo texto:

> "FR-003: A ausência só está confirmada quando o Google responde que o evento não existe ou que está apagado. Qualquer outra resposta é inconclusiva — erro, tempo esgotado, falta de credencial, falha ao renovar o acesso. Nesse caso o sistema NÃO DEVE apagar nem marcar o evento naquele ciclo."

- **Evidência:** service.py:181-191. O token é renovado fora do `try` (128-130, 186). Não há checagem de 'cancelled'. routes.py:4203-4205 trata `None` como `not_found`.

**C4. O estorno de hoje** (spec.md:175-177, 367-369, 381-382)

Novo texto para 175-177:

> "…e o estorno de hoje herda a data e o ciclo da comissão original.
> Ele entra na Planilha do mês seguinte a esse ciclo, que costuma já estar pago. Lá soma na linha do vendedor, baixa o total e a reabre como 'não pago' (ou a faz sumir, se zerar).
> Se alguém marcar a linha como paga de novo, o estorno conta como liquidado sem ter saído de repasse nenhum.
> Na tela de Comissões ele só aparece no mês corrente, e o 'Pagar Mês' de qualquer mês o liquida."

- **FR-025, parêntese:** "(hoje o diálogo diz que a comissão paga 'vira estorno no próximo repasse', e a docstring de aplicar_estorno_comissao diz que a Planilha desconta via _seller_payable_rows — a Planilha não usa essa função)".
- **Ressalva:** comissão legada sem `sale_date` e sem `payable_from` faz o estorno cair no ciclo do cancelamento.
- **Evidência:** cancel_ops.py:135-154; comissoes_ops.py:212-216, 237-251, 370-372, 517-518; financeiro/routes.py:918-944; financeiro_read.py:717-720.

**P3. Devolução em Gastos Extras e o "Pago"** (FR-015a, spec.md:330-331; RBAC, spec.md:392-393; História 3, spec.md:137-138)

Acrescentar:

> "Hoje qualquer 'Salvar' da devolução em Gastos Extras apaga o destinatário 'cliente', o nome e o PIX e liga 'aprovado com edição', mesmo sem mexer no valor. A devolução some da Planilha e do evento. A trava DEVE vir com a correção disso.
> O 'Pago' da devolução é marcado na Planilha de Pagamentos (por item, em massa e na tela antiga), que só troca o estado: não pede comprovante e não grava data, porque o gasto extra não tem essa coluna."

- **Evidência:** GastosExtrasPage.tsx:155-158, 313-316, 563-567; gastos_ops.py:222-238, 424-436; financeiro_read.py:695; financeiro/routes.py:1034, 1170-1177; financeiro_write.py:142-156, 306-318; models.py:1025-1068.

**U1. O cancelado no portal** (FR-022, spec.md:357-358; História 6, spec.md:227-228)

Novo texto:

> "…o evento cancelado sai da agenda, dos convites e do histórico do portal, como hoje.
> A avaliação pós-evento não filtra cancelado. Um cancelado que já terminou e está na janela de 7 dias continua no crachá da aba Histórico, acende o 'Avaliar' e aceita nota pela API. A 303 filtra o cancelado na avaliação (ou registra dívida no docs/05)."

- **Evidência:** portal_ops.py:223, 351-379, 909; portal_rating_ops.py:115-134, 225-236; portal_ratings.py:41; PortalShell.tsx:40; RatingLink.tsx:42.

**G2. Editar evento marcado** (caso de borda, spec.md:251-252; FR-008, spec.md:296-297)

Novo caso de borda:

> "Hoje só a edição de título, data, horário, local ou descrição escreve no Google. Aba Comercial, escala e clientes não tocam o Google.
> Quando o Google falha, o banco já foi salvo. A edição comum vira aviso de falha. A troca de tipo que entra ou sai de SHOW é desfeita e responde 409, e o resto fica salvo. A edição de ensaio responde 500.
> Se o Google aceitar escrita em evento apagado, não sai aviso — o código não permite confirmar."

Nova FR-008:

> "Enquanto marcado, o sistema NÃO DEVE escrever a edição no Google, porque a devolução recria o evento com os dados atuais. A edição salva sem aviso de falha e sem recusar troca de tipo, e a marca continua."

- **Evidência:** event_ops.py:576-596, 638-666, 965, 973-979, 1060-1068, 1679-1688; agenda_write.py:967-968, 1034-1035; calendar/routes.py:2648-2662; app/__init__.py:866-870.

## (b) Ambiguidades para o dono, deduplicadas e ranqueadas por impacto

1. **A vaga automática de Técnico de Som conta como "escalado"?** É a pergunta escolhida (abaixo).
2. **Grupo comercial e satélite** (junta 3 lacunas). O dinheiro pode sair em dobro: "Tudo" no satélite e depois "Tudo" no líder.
   - A comissão proporcional divide por zero no satélite (venda zerada, group_ops.py:173-183).
   - A Premissa (spec.md:485-486) está factualmente errada. `total_recebido` soma só o próprio evento (cancel_ops.py:47-54), e "pago" tem três definições no código.
   - **Padrão proposto:** o satélite cancelado sai sem devolução e sem mexer em comissão ou BV; o dinheiro se resolve no líder. Corrigir a Premissa para "comprovantes do próprio evento".
   - **Resta ao plan:** depois de desagrupar, o "pago" do líder ignora os comprovantes dos ex-satélites (group_ops.py:204-231).
3. **Relatórios do cancelado com retido** (DRE, junto com Dashboard Comercial). A DRE hoje tira o cancelado inteiro e conta a devolução como gasto: mostra −600 quando a Manto ficou com +400 (financeiro_read.py:225-250; vendas_ops.py:154-169). A FR-020 não fecha para a DRE.
   - **Padrão proposto:** a FR-020 passa a valer para Planilha e Comissões. A DRE e o Dashboard ficam como estão, com dívida no docs/05. É a próxima pergunta num clarify futuro.
4. **Evento recriado à mão com id novo** (o caso que motivou a spec). A saída sugerida em spec.md:248-250 ("cancelar o antigo") gera comissão em dobro e cobrança de novo a quem já pagou.
   - **Padrão proposto:** reescrever a recomendação. O Superadmin devolve ao Google o antigo, que tem comprovantes, contrato e escala, e apaga o novo no Google. Se o novo tiver venda, fica marcado e é cancelado com "Nada": pago zero, comissão zero.
5. **Evento marcado sem saída boa e primeira rodada** (junta 2 lacunas). Evento passado já realizado, ou adiado sem data, deixa a faixa acesa para sempre. O primeiro "Limpar eventos fantasma" pode marcar muitos antigos de uma vez (admin_config_write.py:92-106).
   - **Padrão proposto:** ficam só as duas saídas, e devolver ao Google vale mesmo no passado.
   - O plan conta antes do deploy quantos eventos passados com dinheiro já não estão no Google. Se forem muitos, a spec ganha a regra "primeira rodada sem sino".
6. **O que trava na devolução em Gastos Extras** (1 ambiguidade + 2 riscos).
   - **Padrão proposto:** valor, data, vínculo com o evento e exclusão ficam travados. O Financeiro continua corrigindo nome e PIX.
   - A correção do bug que apaga o destinatário 'cliente' é obrigatória.
7. **BV já pago antes do cancelamento.** Mostrar o negociado reescreve o total pago de um mês fechado.
   - **Padrão proposto:** item de BV já pago nunca é reescrito nem escondido (o mesmo princípio da FR-017). Ajustar a FR-019 (spec.md:344-348).
8. **"Próximo repasse" contra "ciclo do cancelamento"** (junta FR-018 e o ciclo do EducaManto). As duas expressões divergem entre os dias 1 e 5 (financeiro_read.py:717-720; comissoes_ops.py:841-858).
   - **Padrão proposto:** "o primeiro repasse do beneficiário ainda não liquidado", para comum e EducaManto. Reescrever FR-018, Entidades (spec.md:381-382) e SC-006.
9. **Devolução "no banco"** (junta 2 lacunas). Conta como paga? E o "desfazer pago" da Planilha?
   - **Padrão proposto:** "no banco" conta como paga, como na FR-017. O "desfazer" continua (financeiro_write.py:142-156).
10. **Desconto maior que o repasse seguinte.**
    - **Padrão proposto:** o item negativo aparece e o financeiro resolve, como a Planilha já faz (routes.py:934-937).
11. **Outros vínculos que o apagamento destrói**: reembolso, nota fiscal, presente 3D (routes.py:259-302; models.py:2297).
    - **Padrão proposto:** a spec fica como está, e o plan conta no manto_local eventos que só teriam esses vínculos.
12. **Evento editado enquanto marcado e depois restaurado da lixeira do Google.**
    - **Padrão proposto:** vale o Google, como hoje. O risco de e-mail de remoção entra nos riscos.
13. **Convite pendente de evento marcado.**
    - **Padrão proposto:** o convite aparece com o aviso e os botões ficam livres.

**Três correções de texto que não precisam do dono:**

- Faixa neutra: "N eventos sumiram do Google Agenda" (spec.md:98-99, 113-114).
- FR-021 exclui a venda virtual, que tem estorno próprio (cancel_ops.py:236-270; virtuais_ops.py:2288-2301; spec.md:464).
- SC-006 (spec.md:456-457) e o invariante do docs/04 (spec.md:477-478) passam a dizer "comissão cheia × retido ÷ venda, nunca acima da cheia", de acordo com a Clarification (spec.md:50-52).

### A pergunta ao dono (a única que cabe)

**Contexto.** Todo SHOW nasce com a vaga "Técnico de Som" já preenchida pelo técnico padrão (talento 42), e o sistema refaz isso a cada sync. A spec adota a regra da 224, e por ela essa vaga conta como "alguém escalado".

**Pergunta.** Quando o sync decide entre apagar e marcar um SHOW que sumiu do Google, essa vaga automática conta?

- **(A) Não conta.** Só conta quem a equipe pôs, inclusive a vaga "Técnico de Som (Presença)" quando designada, ou outro técnico no lugar do padrão. SHOW sem venda, comprovante, contrato, outra pessoa escalada nem grupo é apagado como vazio, como hoje. O botão Excluir da 224 fica como está.
- **(B) Conta.** Todo SHOW que some fica, é marcado, acende a faixa e avisa Superadmin e Comercial, inclusive o SHOW criado por engano ou duplicado. Ele só sai por "Devolver ao Google" ou "Cancelar", porque a 224 recusa excluir. O técnico padrão vê "Evento em confirmação" em todo SHOW marcado.
- **(C) Não conta em lugar nenhum.** Nem no sync, nem no botão Excluir da 224. Um SHOW só com a vaga automática passa a poder ser excluído de vez. Isso mexe no que a spec deixou fora de escopo (spec.md:469).

**Recomendação: A.** A vaga é preenchida pelo sistema, não por decisão de ninguém. Com B, a faixa, que não se dispensa, acende a cada SHOW apagado por engano e perde o efeito de alarme. C resolve também o botão, mas amplia a onda 1.

**Por que esta pergunta vem primeiro:**
- Muda a regra central P1 (FR-001/FR-007) para o tipo de evento mais comum.
- Decide o volume da faixa e do sino, o portal do técnico, o SC-001 e o cenário 7 do verify, que hoje só passa com um evento vazio que não seja SHOW.
- Não dá para adotar um padrão sem o dono: a Premissa (spec.md:482-484) adota a regra da 224 e o Fora de escopo proíbe mudá-la.

**Se a resposta for A:** FR-001, aceite 1.2, SC-001 e a Premissa ganham "fora a vaga de Técnico de Som que o sistema preenche sozinho", e o verify ganha o cenário "SHOW só com o técnico automático → apagado".

**Evidência:** calendar/routes.py:68, 2060-2078, 2274-2275, 2347-2348, 3595; cancel_ops.py:70-73; agenda_write.py:522-527.

## (c) Fatos para o plan (deduplicados)

**Sync e trava**

- **Onde mora a trava.** `_cleanup_stale_events` é o único ponto que apaga por sumiço. Chamadores: sync.py:79 (thread e sync_worker), admin_config_write.py:104, routes.py:474 e verify_205.py:810.
  - `google_event_id` é NOT NULL e UNIQUE (models.py:244).
  - O único id falso é `virtual-local-`, que já é pulado.
- **Consulta de um evento.** Precisa separar três casos: ausente (404/410 ou status 'cancelled'), presente e inconclusivo. O retorno atual tem dois outros consumidores: o Meet das vendas virtuais (virtuais_ops.py:1679) e o botão Sincronizar (routes.py:4203-4206). Mudar o retorno obriga a ajustar os dois, ou a criar uma função nova.
  - O `events.get` devolve evento apagado com status 'cancelled', possivelmente sem título e sem início. Nada em app/ trata isso: service.py:194-214 devolve (None, None).
- **Lista do mês.** Não pagina: faz uma chamada com maxResults=2500 e ignora `nextPageToken` (service.py:148-158). Uma página incompleta faz a limpeza apagar evento vivo. Paginar, ou recusar a limpeza quando vier `nextPageToken`.
- **Mudança de data.** Aplicar na hora da confirmação, não só pular: o horizonte do ciclo automático sai da data velha do banco.
  - `sync_events` e `_mark_talents_worked` fazem commit por conta própria (routes.py:2352, 2358, 2406).
- **Checagem dos marcados.** Tem de ser por id a cada ciclo, não pela lista do mês: um marcado de setembro deixa de ser listado depois de 01/10. E não pode morar em `sync_events` (ver o risco 1).
- **Ciclo e transação.**
  - A thread roda a cada 600 s (app/__init__.py:245); esse é o ciclo da SC-003.
  - "Sincronizar agora" não detecta sumiço.
  - `run_calendar_sync` engole o erro de cada mês sem rollback (sync.py:83-85).
  - `emitir()` usa savepoint e não faz commit.
  - Fixar a granularidade: a FR-003 fala de "o evento", mas o caso de borda e o cenário 13 falam do "ciclo".

**Marca, faixa e sino**

- **Marca num campo próprio**, não em `deletion_requested_*`. Com os campos da 224:
  - o Comercial sobrescreve a marca;
  - "Recusar" zera a marca e o sync marca e avisa de novo, em ciclo;
  - a FK aponta para users e não existe usuário "Sistema";
  - `cancelar_evento` limpa os campos e apaga o rastro;
  - a fila mostra "Pedido por —".
  - Referências: models.py:291-295; cancel_ops.py:194-233, 291-294, 322-366; EventHeader.tsx:313-322, 378-406.
  - Isso implica migration (a spec admite: "a decidir no plan").
- **FR-005 sai de graça** se a marca não tocar em `cancelled_at`: os consumidores financeiros só filtram por `cancelled_at`.
- **Serialização.**
  - Agenda: `serialize_event_summary` cobre mês, dia e busca; o detalhe fica em `serialize_event_detail` (agenda_read.py:70-89, 700-727).
  - Portal: `_role_summary` serializa as três listas (portal_ops.py:268-328). Não reaproveitar o "Ciente" (`event_changed_at`).
- **Faixa.**
  - Fica no AppShell/AppLayout (AppShell.tsx:151-166).
  - Sticky conflita com a régua de abas do evento (EventDetailPage.tsx:242).
  - Endpoint próprio com poll de 60 s sob /api/events/, porque o guard do revendedor dá 403 fora de auth/agenda/events/educamanto (app/__init__.py:739-751).
  - Não pendurar em `useNaoLidas` (COUNT sem join) nem em `useCurrentUser` (sem polling).
- **Sino.**
  - Kind novo no catálogo e em `DESTINATARIOS_POR_KIND`.
  - Limites de coluna: kind 40, dedupe_key 120.
  - A `dedupe_key` carrega o carimbo da marca, não o dia.
  - Regime A, na mesma transação da marca.
  - `marcar_lidas_por_entidade` já existe (notificacoes_ops.py:13-16, 47-61, 137-138, 362-378).
  - Destinatários: COMERCIAL ou SUPERADMIN ativos com `has_access` (82-98).
- **RBAC.** `_can_delete` ignora o "Ver como" e `_role_flags` o respeita (agenda_write.py:83-94; agenda_read.py:149-198). O verify precisa de um COMERCIAL real.

**Devolver ao Google e cancelar**

- **Não existe trava de escrita para evento de show.** `CALENDAR_SUPPRESS_INVITES` só cobre os prazos de figurino (config.py:121-139, 233-236). O plan decide estender essa trava ou criar outra, e isso define os stubs do verify (insert, patch, delete).
- **Recriação.**
  - `insert_event` sempre manda horário: evento de dia inteiro volta com hora (service.py:217-250).
  - Trocar `google_event_id` e `google_html_link` na mesma transação e fazer commit logo, por causa da guarda de 5 minutos (routes.py:2190-2208).
  - Consultar o id velho antes de inserir.
- **Endpoint de cancelar.**
  - Não passa `remover_do_google` (agenda_write.py:541-566).
  - Todo erro vira o campo "motivo".
  - O diálogo pré-preenche `devolucao_sugerida` (cancel_ops.py:99; ExcluirEventoDialog.tsx:105-110), contra a Clarification.
  - `_registrar_devolucao` não tem teto nem exige nome e PIX.
  - `listar_cancelamentos` usa `.first()` (cancel_ops.py:339-350). Somar pela categoria "Devolução a cliente".

**Comissão, BV e dinheiro**

- **O que o cancelamento faz hoje com a comissão** (cancel_ops.py:139-155):
  - a pagar vira cancelada; paga ganha um estorno;
  - no banco fica intacta e é paga cheia;
  - as linhas perdem o `event_id`, e o evento deixa de achar as próprias comissões.
- **Os dois ciclos divergem.**
  - A Planilha usa `coalesce(payable_from, sale_date, created_at)` e inclui no banco.
  - A tela de Comissões usa `sale_date`/`created_at`, sem `payable_from` e sem no banco, e mostra estorno só no mês corrente.
  - `_pending_reversals_query` só pega valor negativo: o ajuste positivo não aparece.
  - Consequência: a FR-020 só fecha comparando por evento. O plan define `sale_date` e `payable_from` das linhas de desconto e de ajuste (comissoes_ops.py:296-340, 358-372, 419-437).
- **Congelar a comissão cheia e a venda no cancelamento.** A cheia é recalculada na hora, e aba comercial e escala do cancelado seguem editáveis (comissoes_ops.py:599-612, 656-686, 852-865). Desconto = soma efetivamente paga − comissão do retido.
- **Tela do evento cancelado.** `comissao_exibida_do_evento` devolve 0 para cancelado (comissoes_ops.py:285-286), e `_compute_kpi` conta a devolução como custo e o BV cheio (agenda_read.py:374-400). As duas precisam de um ramo próprio.
- **BV negociado.** `substituir_acrescimos` apaga e recria os acréscimos a cada gravação (comercial_ops.py:78-117). O valor negociado mora fora do acréscimo, informado por acréscimo, sem sobrescrever `amount_brl`.
- **Venda virtual** não tem `EventPayment`, e `cancelar_evento` não a bloqueia.
- **Textos a reescrever (FR-025):**
  - ExcluirEventoDialog.tsx:31, 67-71, 105, 218-221
  - EventHeader.tsx:372-374
  - models.py:283-289, 383-390
  - cancel_ops.py:128-138
  - eventOps.ts:125-128
  - docs/04:108
  - docs/02:1419
  - GastosExtrasPage.tsx:524-529
  - EventosCancelamentosPage.tsx:29-32

## Riscos de regressão (deduplicados)

1. **Botão "Sincronizar" num evento marcado.** Não tem trava de papel (EventHeader.tsx:206). Com um item vindo só com o id:
   - o título vira "Sem título" e as datas viram None;
   - a reconciliação apaga personagens e manda e-mail de remoção a gente de verdade;
   - se o desmarcar morar em `sync_events`, ele desmarca um evento que continua apagado.
   - "Editar no Google Agenda" abre um link morto.
   - Referências: routes.py:4191-4208, 2229-2236, 2361-2392.
2. **`_sync_commission_payment` cancela a comissão do retido e o ajuste positivo** se ficarem ligados ao evento. Ela roda em toda abertura da Planilha e da tela de Comissões e ao gravar a aba comercial (comissoes_ops.py:793-839, 879-901). O verify tem de reabrir as duas telas depois do cancelamento.
3. **Desconto em ciclo já liquidado.** Reabre o item, e o próximo clique liquida o desconto sem repasse. O "Pagar Mês" pega estorno de qualquer mês (financeiro/routes.py:939-944; comissoes_ops.py:237-251, 516-528).
4. **Gastos Extras destrói a devolução** a cada "Salvar" (P3). Várias devoluções por evento ficam invisíveis por causa do `.first()`.
5. **Consultas sem filtro de cancelado** passam a errar com o volume de cancelamentos: tendência de 6 meses da DRE, recebimentos previstos, nota a emitir e BV da Planilha, nas duas telas (financeiro_read.py:365-385, 425-455, 706-714; financeiro/routes.py:394-415, 464-476, 1043-1051).
6. **Primeiro "Limpar eventos fantasma"** depois do deploy. Pode marcar muitos eventos antigos de uma vez e disparar `_notify_accepted_roles` em evento antigo (routes.py:2339-2342).
7. **Série recorrente editada no Google.** Cada instância pode ganhar um id novo, porque o app não olha `recurringEventId` (service.py:148-156). O resultado seria uma marca por instância.
8. **Verifies e stubs.**
   - O verify_205 passaria a consultar o Google real (verify_205.py:782-810).
   - O cenário 8 precisa de stub de Geocoding e Distance Matrix (routes.py:2319-2335).
   - Apagar um pai vazio cujo ensaio tem EventLog estoura a FK (models.py:352-357; event_ops.py:1715-1724).
9. **Avaliação no portal** aceita evento cancelado (U1). O problema cresce com a 303.
10. **Evento restaurado da lixeira depois de editado no sistema.** O sync sobrescreve os dados, e a reconciliação pelo título apaga roles e manda e-mail de remoção (routes.py:2291-2295, 2350-2392).