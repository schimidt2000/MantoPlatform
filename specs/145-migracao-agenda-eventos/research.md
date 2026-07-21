# Research — Agenda/Eventos leitura (145, US1)

## 1. Reaproveitar vs. reescrever a montagem de dados

**Decisão**: reaproveitar `_build_events_from_db` (agenda) e `_group_events` (grupo comercial)
chamando-os do serviço de leitura. Os cálculos de KPI/cobrança que hoje vivem inline na view
`event_detail` são montados no serviço a partir das mesmas fontes (`SpecialExpense`, acréscimos
BV, `EventPayment`, `EventInstallment`) — replicando a fórmula, não a apresentação.

**Rationale**: `_build_events_from_db`/`_group_events` já são funções reutilizáveis e testadas
em produção; chamá-las é a aplicação direta do Princípio I. Já a montagem de KPI está entrelaçada
com o render da view (variáveis locais passadas ao template), então extraí-la 100% agora
implicaria refatorar a view — risco alto num arquivo crítico. Meio-termo: o serviço replica a
fórmula (bem delimitada) e a verificação por paridade garante que os números batem com a view.

**Alternativa rejeitada**: refatorar `event_detail` inteira para produzir um dict e o template
consumir dele (como fiz com `home()` na 144). Aqui a view é muito maior e mais entrelaçada; o
custo/risco não compensa nesta fatia. Fica como dívida a pagar quando as fatias de escrita
(US2–US5) reescreverem as ações e a view Jinja for finalmente aposentada.

## 2. Shape da serialização do evento (leitura)

**Decisão**: um objeto `EventoDetalhe` com blocos nomeados; blocos financeiros só presentes se
o papel permitir (ver data-model.md). Cada bloco espelha uma seção da tela atual.

**Rationale**: blocos nomeados (em vez de um objeto plano gigante) deixam o RBAC explícito
("bloco `financeiro` só existe se `show_comercial`") e o front condiciona a renderização à
presença do bloco — mesma ergonomia do dashboard da Fundação (seção ausente = sem permissão).

## 3. RBAC: filtrar na API, não no front (NÃO-NEGOCIÁVEL)

**Decisão**: `serialize_event_detail` recebe o usuário + impersonação e decide o que entra no
JSON. Um casting-sem-financeiro nunca recebe `sale_value`, pagamentos, reembolsos, comissão.

**Rationale**: esconder no front deixaria o dado trafegar no JSON (qualquer um abre o DevTools).
A view Jinja hoje já decide isso no servidor (`show_comercial`/`show_financeiro`) — a API tem
que manter a mesma fronteira. É o requisito de maior risco desta fatia (FR-003).

## 4. Recorte da agenda por mês

**Decisão**: `GET /api/agenda?ym=YYYY-MM` (mês), espelhando o parâmetro `ym` da view. Sem
`force_sync` (sync é escrita, US5). `GET /api/agenda/day/<date>` para o dia.

**Rationale**: mantém o modelo mental e a performance da agenda atual (serve do banco, sem rede).
Paginação/infinite-scroll não é escopo — a agenda é navegada por mês.

## 5. Verificação por paridade contra o Jinja

**Decisão**: o script compara a resposta da API com o cálculo da view, por papel, contra
`manto_local`. Foco: totais financeiros (custo, comissão, recebido, reembolso pendente) e a
ausência de blocos financeiros para papel sem permissão.

**Rationale**: "paridade com o que já está no ar" é o critério de sucesso real de uma migração;
comparar contra a fonte viva (Jinja) pega divergência de fórmula que um teste isolado não pegaria.
