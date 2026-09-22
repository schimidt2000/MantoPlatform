# Modelo de dados — Feature 302

**Plano**: [plan.md](./plan.md) · **Pesquisa**: [research.md](./research.md) · **Data**: 2026-09-22

## Migration: NENHUMA

Nenhuma tabela nova, nenhuma coluna nova, nenhum índice novo. `migrations/versions/` não é tocado,
e a head (`e5a1c7d93b20`) não se move. Este documento existe para registrar **o que é lido, de
onde, e com que regra** — porque a feature é de leitura.

## O que a feature lê

### `calendar_events` (`CalendarEvent`, `app/models.py:236-410`)

| Coluna | Tipo | Como a feature usa | Preenchimento no espelho |
|---|---|---|---|
| `start_at` | `DateTime` naive | início, já exibido hoje | 100% |
| `end_at` | `DateTime` naive | **passa a ser exibido** | 475/475 (o espelho inteiro); 64/64 futuros |
| `makeup_time` | `String(5)` `"HH:MM"` | o que **decide** se há linha de maquiagem | 19/475; **0/64 futuros** |
| `makeup_location` | `String(200)` | companhia da hora, **traduzida** (R4) | `manto` (18), `local` (2) |
| `departure_time` | `String(5)` `"HH:MM"` | o que **decide** se há linha de saída | 24/475; **0/64 futuros** |
| `departure_location` | `String(300)` | companhia da hora, com padrão `Manto Produções` | `Manto Produções` (27/27) |
| `parent_event_id` | FK → `calendar_events.id` | liga o ensaio ao show | 54 filhos / 53 pais |
| `event_type` | `String(30)` | filtra `'ENSAIO'` | 98 eventos `ENSAIO` |
| `cancelled_at` | `DateTime` | exclui ensaio cancelado (R12) | 0 ensaios cancelados hoje |
| `location` | `String(500)` | endereço do **ensaio**, lido do filho | 54/54 preenchidos |
| `description` | `Text` | **NÃO é lido** — ver R9 | 40/54, e 23 são "Evento em: …" |

### `event_roles` (`EventRole`, `app/models.py:513-565`)

| Coluna | Tipo | Como a feature usa |
|---|---|---|
| `role_type` | `String(20)` — `'character'` \| `'extra'` | **passa a sair no payload**; decide "Personagem" × "Função" |
| `talent_id` | FK → `talents.id` | já filtra tudo: é o dono da sessão |
| `dismissed_at` | `DateTime` | exclui a vaga dispensada da contagem do aviso interno |
| `invite_status` | `String(20)` | já usado; define a lista de convites pendentes |

Distribuição de `role_type` entre as escalações **com talento** (as que o portal mostra):
`character` 442, `extra` 289 — e os `extra` são Coordenador (144), Técnico de Som (64), Técnico de
Som (Presença) (35), Maquiador (23), Foto/Vídeo (17) e Transporte (5).

## A entidade que não é uma tabela: o ensaio

Um ensaio **não tem modelo próprio**. É um `CalendarEvent` com:

- `event_type == 'ENSAIO'`;
- `parent_event_id` apontando para o show;
- `start_at` / `end_at` próprios — em geral **2 a 4 dias antes** do show;
- `location` próprio, já resolvido para endereço de verdade na gravação
  (`resolve_ensaio_location`, `app/calendar/event_ops.py:1570-1578`) — por isso os 54 têm
  endereço, enquanto a maquiagem guarda código;
- **nenhum `EventRole`**: o elenco fica no show. Por isso o portal, que lista escalações, nunca
  mostrou ensaio.

Existem **44 ensaios órfãos** (sem `parent_event_id`), nenhum deles futuro. Órfão não aparece para
ninguém, e o cenário 12 do verify existe para que essa falha silenciosa tenha nome.

## Regras de leitura (onde mora cada uma)

| Regra | Onde | Por quê |
|---|---|---|
| Linha de maquiagem/saída existe se houver **hora** | `portal_ops._antes_do_evento` | local sem hora é resíduo do formulário: 7 eventos com local de saída e sem horário, 1 na maquiagem (R3) |
| `makeup_location` traduzido | `calendar/event_ops.makeup_location_label` | o banco guarda código; nem tela, nem e-mail, nem WhatsApp podem mostrá-lo (R4) |
| `departure_location` vazio vira `Manto Produções` | constante `DEPARTURE_DEFAULT_LOCATION` em `app/constants.py` | o literal já existe em três lugares (`email_service.py:228`, `event_ops.py:172` e o formulário); vira constante em vez de ganhar um quarto |
| Ensaios ordenados por `start_at` | `portal_ops._antes_do_evento` | a relação `ensaios` não tem `order_by`; o Postgres devolve ordem arbitrária que muda após UPDATE (R12) |
| Ensaio já realizado é excluído | `portal_ops._antes_do_evento` | o bloco é preparação, e a janela "ensaio passado, show futuro" existe sempre — o ensaio cai 2 a 4 dias antes (FR-004a) |
| Bloco só em convites pendentes e futuros | `portal_ops.get_agenda` | preparação é para o que ainda vai acontecer (R11) |
| `before_event` é `None` quando vazio | `portal_ops._antes_do_evento` | a tela testa um nulo, não três coleções (R1) |

## O que **não** muda

- Nenhum filtro de visibilidade: as consultas continuam partindo do `talent_id` da sessão.
- `nao_recusada()` e o filtro de evento cancelado das três listas.
- `events_with_visible_figurino` e a regra do coordenador.
- Os totais do histórico.
- O contrato de dinheiro: `cache_value`, `travel_cache`, `cache_total`, `cache_defined`.
