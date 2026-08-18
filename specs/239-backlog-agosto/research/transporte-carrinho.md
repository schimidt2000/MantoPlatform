# Casting: marcar quem faz transporte fora de SP (carrinho) e somar transporte ao teto

## Resumo
O campo por-pessoa de transporte JÁ EXISTE no banco (`EventRole.travel_cache`, "adicional fora de SP") e já é usado no e-mail de convite e no portal do artista — mas a tela de casting em React NUNCA o envia, e `assign_role` grava `role.travel_cache = parse_brl(None) = None` incondicionalmente: hoje TODO "Salvar" no casting APAGA silenciosamente o adicional de transporte. Nada disso entra no teto: `cache_cap` cobre só `cache_value`, e o `teto_efetivo` da 238 é `max(cache_cap, valor salvo)` sem qualquer parcela de transporte. O que o João pede é (a) um marcador por integrante (o "carrinho") e (b) que o teto desse integrante vire cachê + transporte — nada disso existe; existiu só uma sugestão implícita no Jinja aposentado, onde o campo "Adicional viagem" sugeria km×2×1,9 (custo de UM carro) para o "Coordenador" e km×2÷3 para os demais.

## Causa raiz
app/calendar/casting_ops.py:79-80 — `new_travel = parse_brl(travel_cache); role.travel_cache = new_travel` é executado incondicionalmente, e o único chamador vivo (`app/api/agenda_write.py:138`, alimentado por `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx:239`) nunca manda a chave `travel_cache`. `parse_brl(None)` retorna None (app/money.py:71-72), então todo salvamento de casting grava NULL por cima do adicional de transporte existente. Regressão introduzida na migração do casting para React (o formulário Jinja que mandava o campo, app/templates/event_detail.html:639/647, ficou inalcançável).

## Comportamento atual (evidencia)
TETO (quem define): nasce do orçamento na criação do evento — `app/calendar/routes.py:3266` grava `cache_cap=cap`, vindo de `orc_caches[i][chave_cache]` calculado por `_compute_performer_caches` (`app/calendar/routes.py:2740-2913`). Enforcement único em `app/calendar/casting_ops.py:73-76`: `teto_efetivo = max(role.cache_cap, old_cache_value or 0)` e rebaixa `new_cache` para ele quando `not is_superadmin` (feature 238). O espelho na tela é `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx:166-168`. Papel sem `cache_cap` (evento que não nasceu de orçamento) não tem teto nenhum.

TRANSPORTE JÁ DENTRO DO CACHÊ: `app/calendar/routes.py:2777-2782` calcula `transport_add = km_ida*2/afsp_divisor` (divisor 3,0 em `app/orcamento/settings.py:65`) e soma esse adicional por pessoa em TODOS os `cache_1h..cache_4h`/`cache_custom` de personagens e coordenadores (`app/calendar/routes.py:2841-2845, 2862-2866, 2851-2854`). Ou seja: o "adicional fora de SP por pessoa" JÁ está dentro do `cache_cap` de todo mundo. O que NÃO é distribuído a ninguém é a parcela do veículo (`vt = km_total × tarifa`, `app/orcamento/transport.py:20` van / `:47` carro, tarifas 6,3 / 5,5 / 1,9 em `app/orcamento/settings.py:61-67`).

CAMPO POR PESSOA: `EventRole.travel_cache` Numeric(10,2) — `app/models.py:523`, comentário "adicional fora de SP". Aceito por `assign_role` (`app/calendar/casting_ops.py:34, 79-80`), pelo endpoint JSON (`app/api/agenda_write.py:138`), serializado só para casting (`app/api/agenda_read.py:273`), exibido no e-mail de convite (`app/email_service.py:187-191`) e no portal do artista (`app/talent_portal/portal_ops.py:180-193` com `cache_total = cache_value + travel_cache`; `frontend/apps/portal/src/components/CacheLine.tsx:39-71`).

BUG VIVO (perda de dado): `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx:239` envia só `{roleId, talent_id, cache_value}` — nunca `travel_cache` (o tipo existe em `frontend/apps/internal/src/lib/casting.ts:46` e nunca é preenchido; `grep travel_cache frontend/apps/internal/src` só acha as duas declarações de tipo). `app/api/agenda_write.py:138` repassa `data.get("travel_cache")` = None, e `app/calendar/casting_ops.py:79-80` faz `new_travel = parse_brl(travel_cache); role.travel_cache = new_travel` SEM guarda — `parse_brl(None)` devolve None (`app/money.py:71-72`). Resultado: qualquer "Salvar" no card de casting zera o adicional de transporte já gravado, e ainda dispara e-mail de "Adicional de transporte: R$ X → não definido" para quem já confirmou (`app/calendar/casting_ops.py:130-136, 148-158`).

O FORMULÁRIO QUE TINHA O CAMPO ESTÁ MORTO: `app/templates/event_detail.html:637-653` ainda tem o input `travel_cache` (aparece só se `event.is_outside_sp`) com sugestão `km*2*1.9` para "Coordenador" e `km*2/3` para os demais, e o badge de `app/templates/event_detail.html:589-599`. Mas `/events/<id>` é servido pela SPA interna (`frontend/apps/internal/src/App.tsx:99`), e `frontend/server.js:192-203` só proxia `/api`, `/uploads`, `/catalogo/midia`, `/catalogo/og`, `/portal/photo`, `/google`, `/avaliar`, `/static` para o Flask — a rota Jinja `app/calendar/routes.py:1645-1647` está sombreada.

MARCADORES POR INTEGRANTE HOJE: no card de casting existem Badge "dispensado", `AvailabilityBadge` (conflito/mesmo dia) e Badge de convite — `CastingSection.tsx:190-196, 31-41`. Ícones da casa são emoji (🎭 📱 📋 ✓). Não existe nenhum ícone de carro em lugar nenhum do repo.

DADO DE FORA-SP DISPONÍVEL PARA O CASTING: `event.travel.is_outside_sp` / `distance_km` chegam a todos (`app/api/agenda_read.py:488-503`, montado sem gate em `:554`), já usados em `frontend/apps/internal/src/components/EventDetail/LogisticaSection.tsx:53`. Já `venda.transport_value` (o total de transporte vendido, `app/models.py:317`) só é serializado sob `flags["show_comercial"]` (`app/api/agenda_read.py:722, 727`) — Comercial/Financeiro/Superadmin. O Casting NÃO enxerga esse número hoje.

FINANCEIRO IGNORA `travel_cache`: KPI "Custo (cachês)" soma só `cache_value` (`app/api/agenda_read.py:294`; tela em `ComercialSection.tsx:71`), idem DRE (`app/api/financeiro_read.py:322-325`, `app/financeiro/routes.py:84, 518-522`), a planilha de Pagamentos (`app/financeiro/routes.py:945` `"amount": r.cache_value`) e os CSVs (`app/financeiro/routes.py:1566`, `app/api/financeiro_write.py:523`). Só o portal do artista soma cachê + transporte.

## Arquivos relevantes
- app/calendar/casting_ops.py (28-136 (teto 73-76; wipe do transporte 79-80; e-mail de mudança 130-136, 148-158)) — fonte unica da regra de casting — onde o teto efetivo e o travel_cache sao aplicados; e onde esta a causa raiz do apagamento
- app/models.py (508-550 (cache_value 521, cache_cap 522, travel_cache 523); 306-318 (travel_distance_km 310, is_outside_sp 311, transport_value 317)) — schema: campo por pessoa ja existe; flags de fora-SP e valor de transporte vendido ficam no evento
- app/api/agenda_write.py (117-143 (assign), 213-231 (padrao de toggle figurino-done), 1270-1290 (DELETE do toggle)) — endpoint que alimenta assign_role e o molde exato para o novo toggle do 'carrinho'
- app/api/agenda_read.py (236-274 (serializacao do papel, cache/travel/cap sob show_casting), 294 (KPI de custo), 488-503 (_serialize_travel), 722-727 (venda.transport_value gated)) — onde adicionar does_transport/valor de transporte no payload; mostra que o casting nao ve transport_value hoje
- frontend/apps/internal/src/components/EventDetail/CastingSection.tsx (140-271 (teto 166-168, aviso 260-271, mutate sem travel_cache 237-252, badges por integrante 190-196)) — tela do casting — onde entra o botao/badge do carrinho e o novo calculo de teto
- frontend/apps/internal/src/lib/casting.ts (42-65 (AssignInput com travel_cache nunca usado), 101-131 (useRoleAction, molde do toggle)) — hooks de mutacao do casting
- frontend/apps/internal/src/lib/agenda.ts (119-158 (RoleItem), 150-158 (EventTravel)) — tipos do payload a estender
- app/calendar/routes.py (2740-2913 (_compute_performer_caches; transport_add 2777-2782), 3218-3272 (_create_roles_from_input, cache_cap 3266), 2996-3062 (_build_orcamento_prefill, transport_val via calcular_van/carro)) — origem do teto e do valor de transporte do orcamento — mostra que o adicional por pessoa ja esta dentro do cap e que a parcela do veiculo nao esta
- app/orcamento/transport.py (5-56) — parcelas do transporte: 'transporte' (veiculo) x 'adicional_fora_sp' (por pessoa) x 'adicional_show'
- app/orcamento/settings.py (61-71) — tarifas: van 6,3/5,5, carro_por_km 1,9, afsp_divisor 3,0
- app/templates/event_detail.html (586-600, 636-654) — UI Jinja aposentada que tinha o campo de transporte e a sugestao km*2*1,9 para o Coordenador (motorista implicito)
- frontend/server.js (192-203, 527-537) — prova que /events/<id> vai para a SPA, nao para o Jinja
- app/email_service.py (185-192) — convite ja exibe 'cache + R$ X transporte' quando travel_cache existe
- app/talent_portal/portal_ops.py (167-200) — portal ja soma cache_total = cache_value + travel_cache
- app/financeiro/routes.py (84, 518-522, 937-950, 1566) — planilha de Pagamentos, DRE e CSV pagam/contam SO cache_value — travel_cache fica de fora
- app/calendar/event_ops.py (236-246) — edicao de evento grava cache_value SEM aplicar o teto — buraco existente na regra do cap
- specs/238-teto-autorizado/spec.md (1-40) — regra vigente do teto efetivo (max(cap, valor salvo))
- docs/03_HISTORICO_MUTACOES.md (332-348 (238), 2020-2040 (216, cache_total no portal)) — historico do teto e do cachê+transporte no portal

## Abordagem proposta pela investigacao
1) CORRIGIR O APAGAMENTO ANTES DE TUDO (senão o carrinho nasce zerando dado). Em `app/calendar/casting_ops.py`, trocar o parâmetro `travel_cache` por um sentinela: `_UNSET = object()`; `travel_cache: Any = _UNSET`; e só executar `role.travel_cache = parse_brl(travel_cache)` quando `travel_cache is not _UNSET`. Em `app/api/agenda_write.py:138`, passar `travel_cache=data["travel_cache"] if "travel_cache" in data else _UNSET`. O adaptador Jinja (`app/calendar/routes.py:518`) continua mandando o form.

2) MIGRAÇÃO (1 coluna). Nova revision revisando `c8f4d92e17ab`: `event_roles.does_transport` Boolean nullable (semântica igual a `needs_makeup`/`is_singer`: True ou NULL). Nada a fazer no downgrade além de drop_column.

3) VALOR DO TRANSPORTE DO PAPEL — helper novo em `app/calendar/casting_ops.py` (ou `app/calendar/event_ops.py`), `valor_transporte_papel(event) -> Decimal`, com fallback em cascata, tudo server-side (o Casting não vê `venda.transport_value` hoje):
   a. se `event.orcamento_history_id`: recarrega `form_snapshot` e recalcula com `calcular_van`/`calcular_carro` exatamente como `_build_orcamento_prefill` (`app/calendar/routes.py:3010-3030`), usando a parcela `tb["transporte"]` (veículo) — dividida por `num_carros` quando `transporte_tipo != "van"`;
   b. senão, se `event.transport_value`: usa ele;
   c. senão, se `event.travel_distance_km`: `km*2*carro_por_km` (a mesma sugestão do Jinja morto);
   d. senão 0.
   Guardar sempre `0` quando `event.is_outside_sp` não for True.

4) TETO. Em `assign_role`, `teto_efetivo = max(role.cache_cap, old_cache_value or 0) + (valor_transporte_papel(event) if role.does_transport else 0)`. Manter tudo o mais igual (superadmin livre, papel sem cap sem teto, nota de log). Acrescentar ao `EventLog` a menção "(inclui transporte de R$ X)" quando o papel estiver marcado.

5) ENDPOINT DO CARRINHO — espelho exato de `figurino-done` (`app/api/agenda_write.py:213-231` e `:1270-1290`): `POST /api/roles/<id>/transporte` e `DELETE /api/roles/<id>/transporte`, RBAC `_can_edit_event()`, grava `role.does_transport`, registra `EventLog` ("Marcou/Desmarcou <talento> como responsável pelo transporte"), devolve `_event_detail_json(event)`. Regra de guarda: só aceita quando `event.is_outside_sp` é True.

6) PAYLOAD. Em `app/api/agenda_read.py:_serialize_role`, dentro do bloco `if show_casting:` adicionar `does_transport` (bool) e `transporte_valor` (o resultado do helper, mesmo valor para todos os papéis do evento) — e, para tirar duplicação de regra do front, também `cache_cap_efetivo` já somado. `_compute_kpi` (`:294`) passa a somar `travel_cache` no `cost` se a decisão for que o transporte é custo do evento (ver open questions).

7) FRONT.
   - `frontend/apps/internal/src/lib/agenda.ts:119-148`: `does_transport: boolean; transporte_valor?: number | null; cache_cap_efetivo?: number | null` em `RoleItem`.
   - `frontend/apps/internal/src/lib/casting.ts`: `useToggleTransporte(eventId)` (POST/DELETE via `apiFetch`, `setQueryData(["event", eventId], updated)` como os demais).
   - `CastingSection.tsx` `RoleCard`: quando `data.event.travel.is_outside_sp`, renderizar um botão-toggle 🚗 na linha de ações (ao lado de "Convidar"/"📋 Copiar convite", linhas 273-298) e um `<Badge tone="gold">🚗 Transporte</Badge>` na linha de badges (junto de `AvailabilityBadge`, 190-196). Substituir o cálculo local de `tetoEfetivo` (166-168) por `role.cache_cap_efetivo ?? (cache_cap != null ? Math.max(cache_cap, cache_value ?? 0) : null)`, mantendo o texto do aviso (260-271) intacto — o aviso passa a considerar o transporte sozinho.
   - Passar `travel_cache` no `assign.mutate` só se o campo separado existir (ver decisão 3 nas open questions).

8) VERIFY. `specs/<nova>/verify_XXX.py` no mesmo molde de `specs/238-teto-autorizado/verify_238.py` / `scripts/db/verify_146_casting_write.py`, contra o `manto_local`: (a) salvar sem `travel_cache` NÃO zera o campo; (b) papel marcado aceita cachê até cap+transporte e rebaixa acima disso; (c) papel não marcado segue com o teto da 238; (d) toggle bloqueado em evento dentro de SP.

## Riscos mapeados
- Perda de dado ATIVA hoje: enquanto casting_ops.py:79-80 não for corrigido, qualquer 'Salvar' no casting zera travel_cache e ainda manda e-mail 'Adicional de transporte: R$ X → não definido' para quem já confirmou. Os valores já perdidos não voltam.
- Risco de pagar o adicional fora-SP duas vezes: cache_cap JÁ inclui km×2÷3 por pessoa (routes.py:2777-2782, 2841-2845). Se o 'valor de transporte' do motorista for o event.transport_value INTEIRO, o motorista recebe a parcela por pessoa duas vezes. Só a parcela do veículo (tb['transporte']) é neutra.
- travel_cache não entra em NENHUM número do financeiro: KPI 'Custo (cachês)' (agenda_read.py:294), DRE (financeiro_read.py:322-325), planilha de Pagamentos (financeiro/routes.py:945 paga só cache_value) e CSVs. Se o transporte do motorista virar travel_cache, quem for pagar pela tela de Pagamentos vai pagar a menos — e o lucro do evento fica inflado.
- Teto só existe para evento nascido de orçamento (cache_cap NULL nos demais) — nesses o carrinho não muda limite nenhum, vira só marcador. Pode gerar a impressão de que 'não funcionou'.
- O formulário de EDIÇÃO de evento grava cache_value sem passar por assign_role (event_ops.py:239) — quem tem can_edit_event já contorna o teto por lá hoje; somar transporte ao teto não fecha esse buraco.
- Vários motoristas: com transporte_tipo='carro' e num_carros>1, ou 2 vans, marcar N pessoas com o valor cheio multiplica o custo. Precisa de regra (rateio ou valor por veículo).
- O snapshot do orçamento é a única fonte da parcela do veículo; orçamentos v1 antigos guardavam kmT (ida e volta) e já causaram transporte dobrado uma vez (docs/03_HISTORICO_MUTACOES.md:1615-1620) — o helper precisa usar km_ida como o _build_orcamento_prefill faz.
- Marcar/desmarcar mexe no teto de um papel já salvo acima dele: desmarcar o carrinho pode transformar o valor vigente em 'acima do teto', e o próximo save do casting rebaixa. Pelo invariante da 238 (max com o valor salvo) isso não rebaixa de fato, mas o aviso vermelho vai reaparecer — vale checar o texto.