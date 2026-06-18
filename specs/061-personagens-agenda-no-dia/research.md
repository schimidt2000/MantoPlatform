# Research: Personagens já na agenda no dia (061)

Decisões técnicas. Sem `NEEDS CLARIFICATION`.

## 1. Origem dos "personagens no dia"

- **Decisão**: personagens = `EventRole.character_name` com `role_type == "character"`, juntando
  `CalendarEvent` cujo dia (`start_at::date`) é o dia informado. Distinto por nome.
- **Rationale**: papéis de apoio (Coordenador, Técnico de Som, `PRESENCE_CHARACTER`, Maquiador)
  são criados com `role_type == "extra"` (ver `_ensure_coordinator`/`_ensure_sound_technician`
  em `calendar/routes.py`); filtrar por `role_type == "character"` já os exclui. Ensaios têm
  os roles limpos no sync e seus papéis são "extra" — também excluídos; ainda assim filtramos
  `event_type != "ENSAIO"` por segurança.
- **Vaga sem talento conta**: não filtrar por `talent_id` — a vaga já compromete o personagem no
  dia (FR: "independe de já ter talento atribuído").

## 2. Endpoint de consulta por data

- **Decisão**: novo endpoint JSON no blueprint do orçamento:
  `GET /orcamento/personagens-no-dia?date=YYYY-MM-DD`, protegido por `@login_required` +
  `@_require_vendas` (mesmo acesso da calculadora). Retorna
  `{ "date": "...", "personagens": [ { "nome": "...", "eventos": ["título", ...] } ] }`.
- **Rationale**: separa a consulta (borda HTTP) da UI; reaproveita o decorator de acesso já
  existente. Sem alterar a rota `index`.
- **Comparação de dia**: `func.date(CalendarEvent.start_at) == data` (funciona em SQLite e
  Postgres). Datas inválidas/ausentes → resposta vazia (não erro 500).

## 3. UI: exibir abaixo do campo de data

- **Decisão**: dar `id="event_date"` ao input de data em `orcamento/index.html` e adicionar um
  container (`#agenda-no-dia`) logo abaixo do bloco de data/horário. JS escuta `change` do campo,
  chama o endpoint e renderiza a lista (ou o estado vazio).
- **Rationale**: "aparece logo embaixo"; padrão vanilla JS já usado no projeto. Coloco a função
  em `orcamento.js` (fonte única do JS da calculadora) ou em script da página.
- **Estados**: carregando → lista de personagens (com o(s) evento(s)) → vazio ("Nenhum
  personagem agendado neste dia") → erro silencioso (some).

## 4. Clareza visual (alerta, não bloqueio)

- **Decisão**: bloco de destaque (cor de atenção via variável CSS existente) com rótulo claro,
  ex.: "⚠️ Já na agenda neste dia (não vender em dobro)" + chips/linhas com o nome do personagem
  e o evento.
- **Rationale**: FR-006 (clareza) e premissa de que é informativo, não bloqueia o orçamento.

## 5. Sem mudança de modelo / migration

- **Decisão**: nenhuma. Só leitura de `CalendarEvent`/`EventRole`.
