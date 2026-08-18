# Pagina do evento (parte comercial): link direto para o orcamento que gerou o evento

## Resumo
O evento já guarda a referência ao orçamento de origem (CalendarEvent.orcamento_history_id, FK para orcamento_history), gravada na criação do evento a partir de um orçamento. Só que essa referência nunca sai no JSON de detalhe do evento nem aparece em lugar nenhum da aba Comercial no React — é puramente um campo interno hoje. A rota de destino do link já existe e funciona (/orcamento/:id → OrcamentoResultadoPage), então a implementação é essencialmente: serializar o campo e renderizar um Link.

## Comportamento atual (evidencia)
app/models.py:319 — CalendarEvent.orcamento_history_id é uma FK simples (sem relationship ORM) para orcamento_history.id, nullable. É preenchida em app/calendar/routes.py:3155 e app/api/agenda_write.py:629 no momento da criação do evento (vem do form/JSON como orcamento_history_id — ver app/calendar/routes.py:1433 e event_ops.py:315). O detalhe do evento é servido por GET /api/events/<id> (app/api/agenda.py:131) que chama serialize_event_detail (app/api/agenda_read.py:535). Dentro do bloco `if flags['show_comercial']:` (agenda_read.py:722-752), o dicionário data['venda'] é montado com sale_value, transport_value, clients, form_response etc. — mas orcamento_history_id NÃO está nessa lista (confirmado lendo as linhas 724-752 inteiras). Do lado do frontend, EventoDetalhe (frontend/apps/internal/src/lib/agenda.ts:320+) reflete exatamente esse payload — sem o campo. ComercialSection.tsx (o componente que renderiza a 'parte comercial' da página do evento) tem VendaPanel, ClientesPanel, PreContratoPanel e KpiGrid, e nenhum deles referencia orcamento_history_id ou orçamento (confirmado lendo o arquivo inteiro, 568 linhas). Ou seja: hoje não existe NENHUM jeito de ir do evento até o orçamento que o gerou pela UI — nem o dado chega ao frontend, nem há UI para ele.

## Arquivos relevantes
- app/models.py (319) — linha 319: campo CalendarEvent.orcamento_history_id (FK, já existe, não precisa de migration)
- app/api/agenda_read.py (535-752) — serialize_event_detail — adicionar orcamento_history_id (e opcionalmente um flag de permissão) dentro de data['venda'], no bloco show_comercial
- app/api/agenda_read.py (131-172) — _role_flags — já expõe can_edit_core (COMERCIAL/SUPERADMIN), mesmo conjunto de papéis que _require_vendas do orçamento; útil para decidir se o link deve ser clicável
- app/api/orcamento_read.py (30-33, 204-223) — RBAC de GET /api/orcamento/historico/<id>: _require_vendas (COMERCIAL ou SUPERADMIN) + _get_entry_or_none restringe COMERCIAL não-superadmin a orçamentos que ELE MESMO criou (user_id=current_user.id)
- frontend/apps/internal/src/lib/agenda.ts (320-352 (bloco venda)) — interface EventoDetalhe.venda — adicionar orcamento_history_id: number | null
- frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx (451-546 (VendaPanel)) — VendaPanel — renderizar o link para /orcamento/{id} (react-router Link) quando venda.orcamento_history_id existir; local natural: dentro do Panel 'Comercial — dados da venda', perto do topo, antes ou depois de 'Vendedor responsável'
- frontend/apps/internal/src/App.tsx (134) — confirma a rota de destino já existente: /orcamento/:id → OrcamentoResultadoPage
- frontend/apps/internal/src/pages/OrcamentoHistoricoPage.tsx (70) — referência de como o resto do sistema já faz esse mesmo link (padrão a copiar: <Link to={`/orcamento/${entry.id}`}>Abrir orçamento</Link>)

## Abordagem proposta pela investigacao
Não é bug, é campo existente nunca exposto na UI. Abordagem em 2 pontas, sem migration:

1) Backend — app/api/agenda_read.py, dentro do bloco `if flags['show_comercial']:` (linha ~724), adicionar ao dict data['venda']:
   `"orcamento_history_id": event.orcamento_history_id,`
   Não precisa de query extra (o campo já está carregado no objeto `event`). Se quiser evitar expor um id 'morto' pra quem não pode abri-lo, pode condicionar: só incluir o valor quando `flags['can_edit_core']` for True (mesmo conjunto de papéis — COMERCIAL/SUPERADMIN — que o endpoint GET /api/orcamento/historico/<id> exige); para FINANCEIRO (que vê a aba Comercial mas não tem RBAC pra abrir orçamento) devolver null, e o frontend simplesmente não mostra o link pra esse papel.

2) Frontend:
   - frontend/apps/internal/src/lib/agenda.ts: acrescentar `orcamento_history_id: number | null;` na interface `venda` de `EventoDetalhe`.
   - frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx: importar `Link` de 'react-router-dom' e, dentro de `VendaPanel` (no bloco de leitura, ao lado de 'Vendedor responsável'/'Data da venda'), renderizar quando `venda.orcamento_history_id` existir:
     `<DataRow label="Orçamento de origem"><Link to={`/orcamento/${venda.orcamento_history_id}`} className="text-blue underline">Abrir orçamento</Link></DataRow>`
   Segue o mesmo padrão já usado em OrcamentoHistoricoPage.tsx:70 e evita duplicar layout novo.

3) Nenhuma alteração é necessária na rota /orcamento/:id (OrcamentoResultadoPage) nem no endpoint GET /api/orcamento/historico/<id> — eles já funcionam e mostram os detalhes do orçamento.

Risco a resolver antes de fechar o item (ver risks): a rota que o link abre (GET /api/orcamento/historico/<id>) restringe COMERCIAL não-superadmin a ver só orçamentos que ELE MESMO criou. Se o evento foi vendido por outro comercial (ou o orçamento foi feito por colega), o link vai dar 404 pra quem não é dono nem superadmin — vale decidir se isso é aceitável ou se o RBAC de leitura do orçamento devia se abrir pra qualquer COMERCIAL quando o acesso vem por um evento já vinculado.

## Riscos mapeados
- GET /api/orcamento/historico/<id> (app/api/orcamento_read.py:204-223) só deixa um COMERCIAL não-superadmin ver orçamentos que ELE MESMO criou (filtro user_id=current_user.id). Se o evento foi gerado a partir de um orçamento feito por outro vendedor, o link levará a um 404 'Orçamento não encontrado' para qualquer comercial que não seja o autor nem superadmin — mesmo estando na página do próprio evento que ele vende.
- flags['show_comercial'] (agenda_read.py:148) inclui FINANCEIRO, mas a leitura do orçamento (_require_vendas, orcamento_read.py:30) só libera COMERCIAL/SUPERADMIN — sem tratamento, um usuário FINANCEIRO veria o link e receberia 403 ao clicar. A mitigação proposta (só popular orcamento_history_id quando can_edit_core) evita mostrar um link quebrado, mas então FINANCEIRO nunca vê o vínculo, mesmo sabendo que ele existe.
- Não há relacionamento ORM (db.relationship) entre CalendarEvent e OrcamentoHistory nem ondelete='SET NULL' na FK (migrations/versions/c2d3e4f5a6b7...py:26-29) — excluir um OrcamentoHistory hoje (DELETE /api/orcamento/historico/<id>) não checa se algum evento aponta pra ele; em Postgres de produção isso provavelmente falha com IntegrityError não tratado. Pré-existente ao item pedido, mas o link vai deixar esse acoplamento mais visível/testado.