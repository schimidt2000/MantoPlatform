# Casting: deixar mais claro quando um evento foi fechado com maquiador ou nao

## Resumo
"Maquiador" hoje é só um item de orçamento calculado (calcular_maquiador em app/orcamento/pricing.py, replicado em app/calendar/routes.py:2893-2909) e um checkbox needs_makeup por personagem (app/models.py:539). O flag needs_makeup já viaja até o front (app/api/agenda_read.py:251), mas a tela de Casting que o time usa hoje (frontend/apps/internal/src/components/EventDetail/CastingSection.tsx) nunca lê role.needs_makeup nem sinaliza se a vaga de Maquiador (equipe de apoio) foi de fato preenchida. A tela Jinja antiga (app/templates/event_detail.html:1089-1093) tinha um badge "💄 Maquiador(a) no casting" baseado em has_makeup_role (app/calendar/routes.py:1832-1835, substring "maquiador" no character_name de uma extra role) — esse sinal se perdeu na migração para React (LogisticaSection.tsx atual não tem equivalente).

## Comportamento atual (evidencia)
1) No orçamento, quando pelo menos um artista marca "precisa maquiagem", o sistema calcula um item de custo "Maquiador" (app/orcamento/quote_ops.py:264-269; app/calendar/routes.py:2893-2909, via calcular_maquiador em app/orcamento/pricing.py) — isso é só previsão de preço, não cria vaga de elenco.
2) No formulário de criar/editar evento (ElencoBlock.tsx:79-80), cada personagem tem um checkbox "needs_makeup" que é salvo em EventRole.needs_makeup (app/models.py:539; gravado em app/calendar/event_ops.py:240/254).
3) Não existe nenhuma rotina que crie automaticamente uma EventRole "Maquiador" (role_type='extra') quando needs_makeup é marcado — busquei "Maquiador"/_ensure_makeup em todo app/ e só achei o cálculo de preço; a vaga de Maquiador só existe se alguém adicionar manualmente pela seção "Equipe de apoio" (AddRoleForm em CastingSection.tsx:481-486) digitando o nome livremente.
4) A tela de Casting que o time usa (CastingSection.tsx, dentro de EventDetailPage) lista personagens e equipe de apoio em RoleCard (linhas 140-338) mostrando nome, talento, cachê, convite, disponibilidade — nunca renderiza role.needs_makeup nem qualquer indicação de "precisa de maquiador" ou "maquiador já fechado". O dado needs_makeup chega da API (agenda_read.py:251) e está no tipo RoleItem (frontend/.../lib/agenda.ts:147), mas é usado só nos formulários de criar/editar evento (EventCreatePage.tsx:119, EventEditPage.tsx:126), nunca na visualização de casting.
5) A tela Jinja legada (app/templates/event_detail.html:1078-1093) tinha um badge "Maquiador(a) no casting" controlado por has_makeup_role (app/calendar/routes.py:1832-1835: any role cujo character_name contém "maquiador", case-insensitive) — mas esse sinal só aparece se a vaga já existir; não avisa quando falta criar. E o equivalente React (LogisticaSection.tsx) não reproduziu esse badge condicional.
Resultado: hoje, olhando a tela de Casting no React, não dá para saber (a) se o evento tem algum personagem que precisa de maquiagem nem (b) se a vaga de Maquiador foi de fato fechada (talento atribuído) — exatamente a reclamação do João.

## Arquivos relevantes
- app/models.py (508-539) — EventRole.needs_makeup (linha 539) e role_type extra (linha 508-519) — os campos que sustentam o sinal
- app/api/agenda_read.py (232-262) — _serialize_role já expõe needs_makeup no JSON do evento; é onde adicionar um campo agregado tipo maquiador_status se optar por calcular no backend
- app/calendar/routes.py (1832-1835, 2790-2909) — has_makeup_role e cálculo do item Maquiador no orçamento — precedente de como detectar a vaga por nome
- app/orcamento/quote_ops.py (260-269) — calcular_maquiador usado para o item de orçamento
- frontend/apps/internal/src/components/EventDetail/CastingSection.tsx (140-338, 441-489) — tela real de Casting (RoleCard e CastingSection) — onde falta o badge/indicador
- frontend/apps/internal/src/lib/agenda.ts (119-149) — RoleItem.needs_makeup já tipado, não usado na UI de casting
- app/templates/event_detail.html (1078-1093) — badge legado 'Maquiador(a) no casting', referência de UX que não foi migrada para o React
- frontend/apps/internal/src/components/EventDetail/LogisticaSection.tsx (1-356) — equivalente React da seção de logística/maquiagem — não tem o badge condicional que a versão Jinja tinha
- frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx (79-80) — checkbox needs_makeup por personagem no formulário — origem do dado

## Abordagem proposta pela investigacao
Abordagem sem migração de banco (todos os campos já existem):

1. Backend — em app/api/agenda_read.py (onde o payload do evento é montado, próximo do loop que chama _serialize_role), calcular e incluir um resumo agregado no JSON do evento, ex.:
   "maquiagem": {
     "precisa": bool(algum personagem com needs_makeup=True),
     "fechado": bool(existe extra role cujo character_name bate com 'maquiad' — mesmo critério de has_makeup_role em app/calendar/routes.py:1832 — E que tem talent_id preenchido)
   }
   Reaproveita a regra que já existe no backend legado, sem heurística nova no front.

2. Frontend — em frontend/apps/internal/src/lib/agenda.ts, adicionar esse campo na interface EventoDetalhe (e no resumo de lista de eventos, se o pedido também cobrir lá).

3. Frontend — em CastingSection.tsx:
   a) No cabeçalho do Panel "Casting" (ao lado do badge de conflito de agenda, linha 461-469), Badge condicional:
      - precisa && !fechado → tone "gold"/"red": "Falta maquiador"
      - precisa && fechado → tone "green": "Maquiador fechado"
      - !precisa → nada
   b) Em RoleCard, para personagens com needs_makeup=true, mostrar indicador (ícone 💄 ou Badge pequeno) ao lado do nome — reaproveita role.needs_makeup que já vem da API.
   c) Opcional: destacar (borda) o card da vaga "Maquiador" em "Equipe de apoio" quando existe mas está sem talento — mesmo padrão visual já usado para alerta de disponibilidade (linha 172-176).

4. Se o pedido também cobrir uma visão de lista/agenda (fora do detalhe do evento), seria escopo adicional: replicar o mesmo booleano no serializer da listagem de eventos e um badge no card do evento na agenda — depende de decisão do João (ver open_questions).

Nenhuma migração de banco é necessária — needs_makeup e o padrão de nome "Maquiador" em extra roles já existem; o trabalho é de serialização + UI.
