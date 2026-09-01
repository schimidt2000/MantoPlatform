# Feature 266 — costuras do funil: o lead aparece e tudo leva a tudo

**Branch**: `266-costuras-funil` · **Created**: 2026-08-31 · **Status**: Draft
**Migration**: uma — coluna nullable `form_responses.client_link_source`
(`down_revision` = `e08e454c4780`)

## Problema

O sistema tem os módulos completos e eles conversam mal entre si. O funil de venda
(formulário → orçamento → evento → financeiro → pós-evento) tem degraus manuais onde deveria haver
continuidade, e a continuidade vive na memória de quem opera.

Esta feature ataca as duas quebras mais baratas e mais sentidas no dia a dia:

**1. O lead some.** Uma resposta de formulário não avisa ninguém. O único "aviso" é o link de
WhatsApp que a própria cliente dispara depois de enviar — se ela fechar a página antes do redirect
de 1,2s, a resposta fica salva e invisível até alguém abrir `/formularios` por iniciativa própria.
E quando alguém abre, a resposta está lá **sem cliente associada**, mesmo quando o telefone
normalizado bate com exatamente uma ficha existente: o sistema já sabe quem é, calcula a sugestão,
exibe — e espera um clique manual em cada resposta.

**2. O sistema é um beco sem saída.** O detalhe do evento é o hub do ERP e não navega para lugar
nenhum: o nome da cliente é texto puro, o talento escalado só tem WhatsApp, o pré-contrato vinculado
mostra nome e tipo sem como ler o conteúdo, e os números de comissão não levam ao financeiro. Na
direção oposta, a ficha da cliente esconde o que o banco já guarda — as avaliações dela, por
exemplo, têm filtro pronto no servidor (`GET /api/clientes/avaliacoes?client_id=`) que **nenhuma
tela usa**. Cada conferência vira uma busca manual em outra tela.

Levantamento completo (análise de 31/08/2026, 9 agentes sobre 6 domínios) em
`specs/266-costuras-funil/analise-integracao.md`.

## Solução

Duas frentes, nenhuma migration, nenhum conceito novo — só expor vínculos que o banco já guarda e
ligar dados que já viajam nos payloads.

### Frente A — o lead deixa de ser invisível

1. **Card "Respostas de formulário" na Home** com os contadores que a listagem já calcula:
   respostas sem evento, sem cliente, ambíguas e — a única que é urgência de verdade —
   **festa futura sem evento**. O card leva à `/formularios`.
2. **E-mail de resposta nova** para quem pode agir nela (papéis `COMERCIAL` e `SUPERADMIN` ativos),
   disparado no próprio POST público, com as seções preenchidas.
3. **Auto-associação de cliente por telefone**: quando o telefone normalizado da resposta bate com
   exatamente uma ficha, a resposta já nasce com a cliente vinculada — mesma filosofia do
   auto-vínculo de evento que já existe (só com correspondência única; ambiguidade continua indo
   para revisão manual).
4. **Cliente criada a partir de uma resposta nasce com origem `formulario`** (hoje nasce `manual`,
   e a barra "formulário" do gráfico de origem só conta a carga histórica de importação).
5. **Excluir uma cliente passa a soltar as respostas dela.** `delete_client` limpa `EventClient` e
   `CalendarEvent.client_id`, mas **não** `FormResponse.client_id` — e essa relação não tem backref,
   então o SQLAlchemy não anula o campo sozinho: a exclusão estoura violação de chave estrangeira.
   Hoje o caso é raro (só quem foi associado à mão); com a auto-associação do item 3 ele vira o
   caminho comum. Quem cria a exposição fecha o buraco.

### Frente B — tudo leva a tudo

Seis travessias que hoje não existem, **todas sobre id que já está no payload** — nenhum serializer
muda, nenhum endpoint novo:

| De | Para | Hoje |
|---|---|---|
| Evento → ficha da cliente | `/clientes/:id` | nome em texto puro |
| Evento → ficha do talento | `/talents/:id` | só `wa.me` |
| Evento → pré-contrato | `/formularios?resposta=<id>` | nome e tipo, sem como ler |
| Ficha da cliente → resposta | `/formularios?resposta=<id>` | linha não clicável |
| Ficha da cliente → avaliações dela | card novo na ficha | filtro do servidor ocioso |
| Resultado do orçamento → criar evento | `/events/new?orcamento_id=` | só existe no histórico |

A tela `/formularios` passa a aceitar `?resposta=<id>` e abrir o diálogo de detalhe que já existe —
é o que torna as duas travessias para o pré-contrato possíveis, e por isso é o primeiro item a ser
implementado.

## Decisões

1. **Os contadores do card da Home vêm no payload do dashboard, não numa segunda requisição.** É o
   padrão já estabelecido pelo painel de cobranças pendentes, que também deriva de outro domínio. O
   bloco só é incluído para quem tem o gate de formulários (`COMERCIAL`, `FINANCEIRO`,
   `SUPERADMIN`); para os demais o bloco **não vem no payload e a seção não renderiza** — o padrão
   de RBAC da casa (`docs/00` §4), nunca `if` de papel no cliente.

   O gate do dashboard (`show_comercial`) já resolve exatamente para esse trio, então não há gate
   novo a inventar. A razão decisiva contra chamar `GET /api/formularios/respostas` da Home não é
   estética: aquele endpoint carrega 200 respostas inteiras para entregar 5 inteiros, **e o
   `_require_vendas` dele lê `current_user.roles` cru, ignorando a impersonação** — um SUPERADMIN em
   "Ver como CASTING" continuaria vendo o card. O dashboard respeita o papel simulado.

2. **O card conta o que NÃO foi tratado, não o que é "novo".** `FormResponse` não tem
   `read_at`/`seen_at` — não existe noção de lido no modelo, e forçar o rótulo "nova" em cima de
   `sem_evento` seria uma promessa que o dado não sustenta. Um badge "3 novas desde sua última
   visita" exigiria coluna, migration e endpoint de "marcar como visto": é outra feature. O aviso
   por **e-mail**, esse sim, é por resposta nova — ele dispara no momento da submissão, onde "nova"
   é um fato e não um estado guardado.

3. **O relógio de `futuros_sem_evento` é corrigido junto, não depois.** O filtro usa `date.today()`
   (`formularios_ops.py:145`) e a produção roda em UTC: entre 21h e meia-noite de São Paulo a festa
   de **hoje** já sai da contagem. Hoje o erro vive numa tela interna; levar o número para a Home
   sem corrigir seria instalar um número errado na primeira tela do sistema. Passa a `now_sp()`.

4. **As mutações de `/formularios` passam a invalidar `["dashboard"]`.** Sem isso, vincular ou
   associar uma resposta deixa o card da Home com o número velho até um refetch por foco de janela —
   e o `staleTime` de 30s com `refetchOnWindowFocus: false` faz o dado errado *persistir* em tela.
   Um contador que não acompanha a ação parece que a ação não salvou.

5. **O e-mail de resposta nova vai por papel, não para todo mundo interno.** Uma resposta de
   formulário é um lead comercial; mandar para `CASTING` e `FIGURINO` transformaria o aviso em ruído
   e o time aprenderia a ignorá-lo. Destinatários: usuários ativos com papel `COMERCIAL` ou
   `SUPERADMIN`, reusando a validação de destinatários internos dos auditores.

6. **Um e-mail por resposta, sem digest.** O volume de leads é de poucas unidades por dia e o lead é
   perecível — agrupar num resumo diário destruiria a única vantagem do aviso, que é chegar a tempo
   de responder a cliente no mesmo dia.

7. **A falha do e-mail nunca derruba a submissão.** O envio é assíncrono (`send_async`) e o POST
   público responde 201 independentemente — a resposta da cliente já está gravada antes, e perder um
   lead porque o SMTP caiu seria pior que não ter o aviso. Mesma filosofia do auto-vínculo, que já é
   best-effort.

8. **A auto-associação de cliente só acontece com correspondência única.** É a mesma regra do
   auto-vínculo de evento, e pela mesma razão: vincular a ficha errada é pior que não vincular, e o
   telefone é a identidade única do CRM. Dois clientes com o mesmo telefone não existem
   (`Client.phone` é UNIQUE), então "exatamente um" é o caso normal — o caso vazio simplesmente não
   associa e segue para revisão manual como hoje.

9. **A auto-associação roda no submit, não só quando há evento.** O vínculo de cliente e o de evento
   são independentes: uma cliente recorrente que preenche o formulário três meses antes da festa
   deve chegar identificada mesmo sem evento nenhum na agenda ainda.

10. **A associação automática é distinguível da manual — e isso custa uma coluna.** Não existe hoje
    equivalente de `event_link_source` para cliente; sem ele, um vínculo que a máquina deduziu fica
    indistinguível de um que a comercial conferiu, e o item vira irreversível na auditoria. O caso
    que justifica a coluna é real: duas pessoas que dividem um telefone (a mãe que reserva pela
    amiga) produzem um match único e **errado** — a comercial precisa saber que aquilo foi deduzido
    para conferir. Entra `form_responses.client_link_source` (`String(20)`, nullable, valores
    `'auto_phone' | 'manual'`), gravada também por `associate_client` e zerada por
    `dissociate_client`. É aditiva e nullable: nenhuma linha existente precisa de backfill.

11. **A auto-associação NÃO entra no reprocessamento do sync.** `retry_auto_link_pending` filtra por
    `event_link_locked`, que não sabe nada sobre cliente — estendê-lo faria o robô religar, a cada
    ciclo de 10 minutos, a cliente que a comercial acabou de desassociar. O vínculo automático de
    cliente acontece **uma vez, no envio**, e nunca mais. Corrigir isso "depois" seria repetir
    exatamente o defeito que a feature 267 vai consertar no vínculo de evento.

12. **O vínculo automático nunca cria cliente.** O endpoint de submissão é público e sem
    autenticação; deixá-lo criar linha em `clients` seria porta aberta para poluir o CRM. Ele só
    aponta para ficha existente. Criar continua sendo ação humana, pela tela.

13. **Quando o evento também é vinculado na mesma passada, a cliente entra no evento.** É o que o
    caminho manual (`link_event`) já faz via `ensure_event_client`. Deixar o caminho automático se
    comportar diferente criaria uma segunda assimetria manual↔automático — justamente o tipo de
    defeito que a 267 existe para eliminar. Efeito colateral assumido conscientemente: se o evento
    ainda não tem cliente nenhum, essa cliente entra como **Contratante**.

14. **Nenhum link novo abre em aba nova, e o "voltar" fecha o diálogo.** A navegação é interna ao ERP.
    Abrir `?resposta=` entra no histórico (push) e fechar remove o parâmetro (replace): o botão
    voltar do navegador fecha o diálogo em vez de sair da tela, que é o modelo mental de quem abriu
    uma ficha. Fechar **sempre** limpa o parâmetro — inclusive no caminho da exclusão, senão um F5
    depois de excluir reabriria o diálogo num id morto, em erro permanente.

15. **O card de avaliações da ficha não repete o cálculo.** Consome o endpoint existente com o
    parâmetro que ele já aceita — zero código novo de servidor. É o exemplo mais puro do que esta
    feature é: o trabalho já foi feito, faltava a tela pedir.

16. **O link do talento cobre os dois cards, não um só.** O elenco aparece em dois lugares na aba
    Produção — o card do personagem e o card de presença (feature 239). Linkar só um deixaria a
    mesma pessoa clicável numa lista e morta na de baixo. O avatar leva `aria-label` explícito
    porque o `AvatarThumb` é decorativo (`aria-hidden`, `alt=""`) e um link só em volta dele seria
    anunciado como "link" vazio pelo leitor de tela.

17. **O nome nulo não vira link.** Cliente sem nome cadastrado renderiza "—"; um link cujo texto é
    um travessão não diz para onde vai. Nesse caso o texto continua sendo texto.

18. **O link para comissões sai desta feature.** As telas financeiras são `/financeiro/comissoes` e
    `/financeiro/pagamentos`, e **nenhuma das duas lê parâmetro de URL hoje** — o deep-link útil
    exigiria converter as duas para estado-na-URL, com três armadilhas próprias (o mês da comissão é
    o da **venda** e o do pagamento é o do **evento**; o filtro de vendedor é privilegiado e o
    servidor o ignora para `COMERCIAL`; a aba padrão esconderia o filtro). Um link que cai numa tela
    sem filtro é pior que link nenhum. Vai para a **267**, onde a comissão do evento já será
    reconciliada com a real — é a mesma história contada inteira.

19. **O card de avaliações diz de quais eventos ele fala.** `summarize_feedback` filtra por
    `CalendarEvent.client_id` — o FK do **contratante** — enquanto o card "Eventos" logo acima da
    mesma tela lista pela associação múltipla `EventClient`. Uma cliente que entra num evento só como
    assessora veria "nenhuma avaliação" com eventos listados acima. Corrigir o filtro mudaria a
    semântica da tela `/clientes/avaliacoes` inteira (KPIs, distribuição, atenção) e pede verificação
    própria — não cabe numa feature de costura. Aqui o estado vazio diz a verdade: *"nenhuma
    avaliação nos eventos em que ela é a contratante"*. A unificação fica registrada para a onda 2.

## Verificação

Script `specs/266-costuras-funil/verify_266.py` contra o `manto_local` (**nunca** o SQLite de
`instance/`), escrito **antes** da implementação (Princípio VIII). Cobertura mínima:

- submissão pública com telefone de cliente existente → resposta nasce com `client_id` correto;
- submissão com telefone desconhecido → `client_id` nulo, sem erro, resposta salva;
- submissão com telefone que não bate com ninguém e com evento na data → vínculo de evento continua
  funcionando como antes (não regredir o auto-vínculo);
- vínculo automático grava `client_link_source == "auto_phone"`; associar pela tela grava
  `"manual"`; desassociar zera os dois campos;
- excluir uma cliente que tem resposta de formulário **conclui sem erro**, e a resposta reaparece na
  fila "sem cliente" com os dados intactos (é o teste que hoje falha com `IntegrityError`);
- submissão com telefone conhecido **e** evento na data → a cliente entra em `event_clients`
  (paridade com o caminho manual `link_event`);
- criação de cliente a partir de resposta → `source == "formulario"` **e** a barra "formulário" do
  gráfico de origem sobe (as duas metades da mudança: o valor gravado e o mapa que o traduz — o
  `source_keys.get(source, "manual")` joga valor desconhecido no balde Manual e faria a troca ser
  invisível);
- payload do dashboard: bloco de formulários presente para `COMERCIAL`/`SUPERADMIN` e **ausente**
  para `CASTING` (RBAC por ausência de chave, não por 403);
- contadores do card conferem com a listagem de `/formularios` para o mesmo estado de banco;
- e-mail: destinatários resolvidos são só `COMERCIAL`/`SUPERADMIN` ativos, e falha de envio **não**
  altera o status 201 da submissão.

Na tela (`manto_local`, superadmin), com viewport desktop e mobile:

- do detalhe de um evento com cliente, talento e pré-contrato: os links levam ao destino certo e o
  botão voltar retorna ao evento; o talento é clicável tanto no card do personagem quanto no de
  presença; cliente sem nome não vira link;
- `/formularios?resposta=<id>` abre o diálogo daquela resposta direto, inclusive em carregamento
  frio (URL colada, sem passar pela listagem);
- ficha da cliente: linhas de "Festas anteriores" clicáveis e card de avaliações com dados reais;
- `/orcamento/:id` → "Criar evento" chega em `/events/new` já pré-preenchido;
- Home: card aparece para superadmin com os contadores certos e some ao simular `CASTING` no
  "Ver como".

Ensaio da migration antes do merge: restaurar o dump mais recente num banco descartável e rodar o
`startCommand` inteiro (`flask db upgrade && python seed.py`), como na feature 235 — a coluna é
aditiva e nullable, mas o ensaio é o que prova que o head está encadeado certo.

Portões da constituição: `npx tsc --noEmit` limpo nos **três** apps (`cd frontend && npm run
typecheck`), `ruff check` limpo, migration manual com `down_revision` no head atual, e `docs/01`,
`docs/02` e `docs/03` atualizados ao fim do ciclo.

## Fora de escopo

Fica para a **feature 267** (integridade e dívida P0/P1, já mapeada e planejada em conjunto):
unificar os dois caminhos de vínculo evento↔resposta (hoje o caminho da agenda não marca
`event_link_locked` e o re-vínculo automático do próximo sync desfaz a decisão humana em silêncio);
exclusão de evento limpando o rastro da resposta; o deep-link do evento para `/financeiro/comissoes`
(que exige converter as duas telas financeiras para estado-na-URL — decisão 15); os **demais**
relógios UTC em código de negócio
(`dashboard_cutoff`, `resolve_performance_period`, o KPI "novos este mês" da lista de clientes — aqui
só o filtro que a Home passa a exibir é corrigido); e as quatro correções de comissão que a dívida
técnica já prescreve — marcar pago da comissão
EducaManto (`docs/05` #1, P0), invalidação completa do cache financeiro (#2, P0), venda preenchida
pela tela de edição completa que não gera comissão (#6, P1) e o lucro do evento que usa uma quarta
fórmula divergente (#5, P1).

Fica para as ondas seguintes (já mapeadas na análise, não planejadas ainda): FK e status no
orçamento com `ClientPicker`, prefills ricos nos quatro sentidos, `EducaManto → evento`, baixa de
parcela e a rotina de lembretes por data, avaliação D+1 automática, reativação por aniversário,
mesclagem de clientes duplicados e busca global.

**A única mudança de schema é a coluna da decisão 10** — aditiva, nullable, sem backfill. Todo o
resto é UI sobre payload que já viaja e escritas que o banco já comporta. É o que mantém esta
feature publicável rápido e com janela de 502 curta.

Também não entra: notificação de "resposta não lida" com badge de contagem (exigiria coluna de
leitura, endpoint de marcar-como-visto e uma decisão de UX própria — decisão 2) e a unificação do
filtro de avaliações entre contratante e `EventClient` (decisão 19).
