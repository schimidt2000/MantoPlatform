# Contratos — 303: o sync não apaga evento com venda

**Spec**: [../spec.md](../spec.md) · **Modelo**: [../data-model.md](../data-model.md) ·
**Pesquisa**: [../research.md](../research.md)

Todo campo novo em payload que já existe nasce **opcional** no TypeScript (`campo?:`) — backend e
bundle sobem separados. Erros usam o envelope de `json_error`
(`{"error": {"message", "fields"?, ...extra}}`). O verify copia os caminhos e o nome da coluna daqui.

## Nomes fixados (o verify depende deles)

| O quê | Nome |
|---|---|
| Coluna da marca | `calendar_events.google_missing_since` |
| Chave da trava | `CALENDAR_SUPPRESS_EVENT_WRITES`, lida de `current_app.config` a cada chamada |
| Consulta ao Google | `app.calendar.service.consultar_evento` |
| Kind do sino | `evento.sumiu_google`, entidade `calendar_event` |
| Situações | `cancelado`, `sumiu_do_google`, `exclusao_solicitada` |
| Ações de auditoria | `sumiu_do_google`, `google_reapareceu`, `google_returned`, `google_return_failed`, `presente_fora_da_lista` |

## Endpoints novos

### `GET /api/events/sumidos-google` — a faixa

- **Módulo**: `app/api/agenda.py`. **RBAC**: `api_login_required`; `_ve_faixa_sumidos()` = SUPERADMIN
  ou COMERCIAL **pelo papel efetivo** (`_role_flags(current_user, session.get("impersonate_role"))`).
  Quem não passa recebe **200** com a faixa vazia — nunca 403.
- **Resposta 200**

```json
{ "pode_ver": true, "total": 2, "limit": 100,
  "items": [ { "id": 1244, "title": "(R&I) GABBY + PANDY + GATUNO", "start_at": "2026-09-19T15:00:00" } ] }
```

  `total` é a contagem exata de eventos marcados e não cancelados; `items` vem ordenado por urgência
  (futuros por data crescente; depois passados, do mais recente ao mais antigo; sem data por
  último). "Passado" é o evento cujo fim (ou o início, se não houver fim) é anterior a agora em São
  Paulo — o mesmo corte do aviso de data passada do diálogo. Sem dinheiro. Quem não vê: `{"pode_ver": false, "total": 0, "limit": 100, "items": []}`.
- **Erros**: 401 sem sessão.
- **TypeScript** (`lib/sumidosGoogle.ts`): `interface SumidoGoogle { id: number; title: string;
  start_at: string | null }`; `interface FaixaSumidos { pode_ver: boolean; total: number; limit:
  number; items: SumidoGoogle[] }`.

### `POST /api/events/<int:event_id>/devolver-ao-google`

- **Módulo**: `app/api/agenda_write.py`. **RBAC**: `_can_delete()` (SUPERADMIN real), depois do 404.
  Corpo vazio.
- **Resposta 200**: o detalhe do evento (`serialize_event_detail`) mais
  `"devolucao_google": {"resultado": "recriado" | "reapareceu"}`.
- **Erros** — `{"error": {"message": <pt-BR>, "codigo": <str>}}`

| Status | `codigo` | Quando | Mensagem |
|---|---|---|---|
| 404 | — | evento não existe | (a do 404 de hoje) |
| 403 | — | sem permissão | (a do 403 de hoje) |
| 409 | `cancelado` | evento cancelado | `Este evento está cancelado e não pode ser devolvido ao Google Agenda.` |
| 409 | `nao_marcado` | o evento não está marcado (inclusive segundo clique) | `Este evento não está mais marcado — já foi devolvido ou voltou ao Google Agenda.` |
| 409 | `venda_virtual` | defensivo — venda virtual nunca é marcada | `Venda virtual não é devolvida ao Google Agenda por aqui.` |
| 409 | `sem_data` | sem início ou fim, ou fim antes do início | `Acerte a data e o horário do evento antes de devolvê-lo ao Google Agenda.` |
| 409 | `google_travado` | ambiente com a trava de escrita ligada — nenhuma chamada ao Google | `Este ambiente não escreve no Google Agenda. Nada foi alterado.` |
| 502 | `google_inconclusivo` | a consulta ao id velho não foi conclusiva | `O Google Agenda não respondeu à conferência. Nada foi alterado — tente de novo em alguns minutos.` |
| 502 | `google_desconectado` | Google não conectado ou credencial revogada | `O sistema está sem acesso ao Google Agenda. Nada foi alterado.` |
| 502 | `google_recusou` | o Google não confirmou a criação | `O Google Agenda não confirmou a criação. A marca continua. Antes de tentar de novo, confira na Agenda se o evento apareceu — se apareceu, apague-o lá e devolva de novo.` |
| 502 | `google_recusou` | o Google não aceitou a atualização, no ramo "reapareceu" | `O evento já está no Google Agenda, mas o Google não aceitou a atualização. A marca continua — tente de novo.` |

  Em todo erro a marca e o `google_event_id` ficam como estavam. Nenhuma mensagem traz o erro bruto.
  O 404 é da view, antes do núcleo; se o evento sumir entre a view e o bloqueio, o núcleo levanta o
  código interno `inexistente`, que a view traduz no mesmo 404, sem `codigo` no corpo.
- **TypeScript**: `devolucao_google?: { resultado: "recriado" | "reapareceu" }` em `EventoDetalhe`;
  `codigo` como união literal.

## Endpoints alterados

| Endpoint | O que muda |
|---|---|
| `POST /api/events/<id>/sync` | Confere o próprio evento no Google antes de mexer. Ausência confirmada → **409** "Este evento não está mais no Google Agenda. Nada foi alterado." (para qualquer evento, marcado ou não). Inconclusivo → 502, como hoje. Presente → sincroniza como hoje e, se estava marcado, retira a marca. Segue sem gate de papel. |
| `PATCH /api/events/<id>` e `PATCH /api/events/<id>/basico` | Evento marcado: 200, **sem** escrita no Google, sem aviso de falha em `warnings`, sem desfazer troca de tipo (nunca 409 por isso). |
| `POST /api/events/<id>/cancelar` | Evento marcado: **409** `{"message": "Este evento sumiu do Google Agenda. O cancelamento com devolução do dinheiro chega na próxima entrega — por enquanto, devolva-o ao Google Agenda.", "codigo": "sumiu_do_google"}`. Demais eventos: como hoje. |
| `DELETE /api/events/<id>` | Evento marcado: **409**, mesma mensagem e `codigo`. Demais: como hoje, exceto o evento vazio com ensaio-filho que tem histórico, que deixa de estourar e é excluído. A recusa mora em `_delete_event_flow`: a view só aplica o 409 de "use o cancelamento" (`pode_excluir`) quando o evento **não** está marcado — o marcado segue para o núcleo, que levanta antes de qualquer escrita. A rota antiga `POST /events/<id>/delete` (Jinja, só pelo backend direto) recusa pela mesma regra, com mensagem de erro e volta ao evento. |
| `POST` e `DELETE /api/events/<id>/solicitar-exclusao` | Sem mudança: valem para evento marcado e não alteram `google_missing_since`. |
| `POST /api/admin/sync/run` (`action: "cleanup_past"`) | `results[]` ganha `marcados?`, `movidos?`, `desmarcados?`, `inconclusivos?`, `falhas?` (números); `ok` é falso quando há falha; a `message` passa a dizer os seis números da FR-042 (removidos, mantidos e marcados, com data atualizada, de volta ao Google, sem confirmação, com falha — texto em §Textos fixos). `sync_now` não muda. RBAC inalterado (SUPERADMIN). |
| `GET /api/agenda`, `GET /api/agenda/day/<data>`, `GET /api/agenda/search` | Cada evento do resumo ganha `situacao?: SituacaoEvento \| null` e `situacao_desde?: string \| null`. Sem dinheiro, sem motivo, sem autor. |
| `GET /api/events/<id>` | `event.situacao?`; `event.sumiu_do_google?: { desde: string } \| null` (não nulo só quando marcado e não cancelado); `event.google_html_link` vem `null` quando o evento está marcado ou cancelado. |
| `GET /api/portal/agenda` (`pending_invites`, `upcoming`, `history`) e `GET /api/portal/historico` (`items`) | Cada item ganha `em_confirmacao?: boolean`. Vai o código, nunca o motivo. |
| `GET /api/portal/ratings/pending` | `rateable_event_ids` e `editable_event_ids` nunca trazem evento cancelado. |
| `GET\|POST /api/portal/events/<id>/rate`, `POST …/rate/detail` | Evento cancelado: **400** "Este evento foi cancelado e não recebe avaliação." |

`type SituacaoEvento = "cancelado" | "sumiu_do_google" | "exclusao_solicitada"` — um `export` só, em
`frontend/apps/internal/src/lib/agenda.ts`.

## Núcleo (`app/calendar/sumico_ops.py`, novo)

```python
@dataclass(frozen=True)
class PresoAoEvento:
    venda: Decimal; recebido: Decimal; n_comprovantes: int
    tem_contrato: bool; n_escalados: int; grupo: str | None
    tecnico_automatico: bool    # SHOW com a vaga automática do técnico padrão (não conta em n_escalados)
    @property
    def vazio(self) -> bool: ...
    def descricao(self) -> str: ...

@dataclass
class ResultadoLimpeza:
    removidos: list[str]; marcados: list[int]; movidos: list[int]; desmarcados: list[int]
    presentes_fora_da_lista: list[int]; inconclusivos: list[int]; falhas: list[int]

def preso_ao_evento(event: CalendarEvent) -> PresoAoEvento
def filtro_marcados() -> ColumnElement[bool]                       # marca preenchida E não cancelado
def marcar(event, preso: PresoAoEvento, *, contexto: str) -> datetime | None   # None = outro processo marcou
def desmarcar(event, *, motivo: str, actor_name: str = "Sistema", actor_role: str = "Sistema") -> bool
def limpar_mes(items: list[dict], year: int, month: int) -> ResultadoLimpeza
def reconferir_marcados() -> dict[str, list[int]]    # reapareceram, seguem_ausentes, inconclusivos, falhas
def mesmos_dados(event: CalendarEvent, item: dict) -> bool   # compara pelos valores que sync_events gravaria (R5)
def faixa_sumidos(limite: int = FAIXA_LIMITE) -> dict[str, Any]
def devolver_ao_google(event_id: int, *, actor: User) -> dict[str, Any]   # levanta DevolverAoGoogleError(codigo, message)
```

- `marcar` e `desmarcar` **não comitam**; quem comita é o passo do evento em `limpar_mes`, a
  reconferência, o fluxo do "Sincronizar" e a devolução.
- `marcar(..., contexto=)`: `contexto` é o mês limpo, `AAAA-MM`, gravado no detalhe da auditoria.
- `desmarcar(..., motivo=)`: `motivo` é um valor fechado — `MOTIVO_REAPARECEU` ou
  `MOTIVO_DEVOLVIDO`. Nos dois, zera a coluna e marca o aviso do sino como lido; devolve `False`
  sem escrever se o evento não está marcado. Só no **reaparecimento** grava o rastro (histórico
  "Reapareceu…" com o ator recebido, cortado em 60 caracteres, e a auditoria `google_reapareceu`);
  na **devolução** o rastro é o que a própria devolução já gravou antes de chamar o Google (R13).
- Comissão já paga **não** entra em `PresoAoEvento` (decisão do dono, 30/09): o evento sem mais
  nada é apagado e o estorno sai contra o vendedor, como hoje.
- `_sync_single_event_flow(event, *, actor_name="Sistema", actor_role="Sistema")` (em `routes.py`):
  os dois adaptadores passam quem clicou, para o histórico do reaparecimento.
- O disjuntor é estado local de cada chamada de `limpar_mes` e de `reconferir_marcados` (R4): não há
  estado compartilhado entre meses.
- FR-045: `EventoMarcadoError(CancelValidationError)`, nova em `app/calendar/cancel_ops.py` (ao lado
  da classe-mãe, `:39`), levantada por `cancelar_evento` e por `_delete_event_flow` (em `routes.py`)
  para evento marcado, antes de qualquer escrita. A API a captura **antes** da `CancelValidationError`
  e responde 409 com `codigo: "sumiu_do_google"`; o wrapper Jinja a traduz em mensagem de erro.
- O Google é chamado sempre por atributo do módulo (`from app.calendar import service as gcal`;
  `gcal.consultar_evento(...)`, `gcal.insert_event(...)`), com os helpers de `routes.py` por import
  tardio.
- `app/calendar/routes.py::_cleanup_stale_events(items, year, month) -> ResultadoLimpeza` — mesmo
  nome e mesma entrada; o corpo é `return sumico_ops.limpar_mes(items, year, month)`.

## Google (`app/calendar/service.py`)

```python
@dataclass(frozen=True)
class ConsultaEvento:
    desfecho: str               # "presente" | "ausente" | "inconclusivo"
    item: dict | None = None    # só em "presente"
    motivo: str = ""            # lista fechada, abaixo

def consultar_evento(calendar_id: str, google_event_id: str) -> ConsultaEvento   # nunca levanta
def insert_event(calendar_id, title, start_dt, end_dt, description="", location="",
                 conference_request_id=None, *, all_day: bool = False) -> dict
```

`motivo`, por desfecho — ausente: `http_404`, `http_410`, `cancelled`; presente: vazio ou
`serie_recorrente`; inconclusivo: `sem_credencial` (credencial ausente, falha ao renovar, HTTP 401),
`rede` (erro de conexão ou tempo esgotado), `http_5xx`, `http_403`, `http_429`, `http_4xx` (os
demais) e `sem_inicio`. Abrem o disjuntor: `rede`, `http_5xx` e `sem_credencial`. Como a função
nunca levanta, o inesperado também tem classe: qualquer exceção ao carregar a credencial, e
`google.auth.exceptions.RefreshError` em qualquer ponto — inclusive no `.execute()`, que é onde a
renovação do token acontece hoje → `sem_credencial`; qualquer outra que não seja erro HTTP → `rede`
(abre o disjuntor: direção
segura), com o tipo do erro no `logger.warning`. Cada chamada carrega a credencial e monta o cliente
(não há cliente compartilhado entre consultas: a falha de credencial tem uma regra só).

`fetch_single_event` não muda (o Meet da Loja Virtual depende dela).

## Sino (`app/notificacoes/notificacoes_ops.py`)

```python
KIND_EVENTO_SUMIU_GOOGLE = "evento.sumiu_google"
DESTINATARIOS_POR_KIND[KIND_EVENTO_SUMIU_GOOGLE] = (RoleName.COMERCIAL, RoleName.SUPERADMIN)

def notificar_evento_sumiu_google(event: CalendarEvent, *, marcado_em: datetime, preso: PresoAoEvento) -> int
    """Regime A, não comita. Devolve quantas linhas gravou."""
```

Título: `Sumiu do Google Agenda — <título do evento>`. Corpo:
`15/11/2026 · venda R$ 2.000,00 · recebido R$ 1.000,00 · 3 pessoas escaladas`, com as variantes
`sem data`, `sem venda`, `parte de grupo comercial`, `1 pessoa escalada`, `ninguém escalado`,
`· contrato anexado` (quando há contrato) e `recebido R$ 0,00 (N comprovante(s) sem valor)` (quando
há comprovante e a soma é zero).
Frontend: `ICONE_POR_KIND["evento.sumiu_google"] = CalendarX`. Na linha do sino (painel e
`/notificacoes`) o aviso `urgent` não é cortado em uma linha: o título quebra em até duas linhas e o
corpo em até três (`line-clamp` no lugar do `truncate`), com o texto inteiro no `title`. Os avisos
`info` continuam como hoje. No bundle antigo o kind novo cai no ícone padrão (`?? Bell`, como hoje).

## Frontend — hooks

```ts
// lib/sumidosGoogle.ts
export function useSumidosGoogle(): UseQueryResult<FaixaSumidos>
//   queryKey ["sumidos-google", user.id]; refetchInterval 60 s enquanto pode_ver !== false;
//   refetchIntervalInBackground false; retry false — montado SÓ no AppShell
export function useFaixaSumidosVisivel(): boolean     // observer passivo: enabled false + select
export function invalidarSumidosGoogle(queryClient: QueryClient): void

// lib/eventOps.ts
export function useDevolverAoGoogle(eventId: number): UseMutationResult<EventoDetalhe, ApiRequestError, void>
//   onSuccess: setQueryData(["event", id]) + invalidar agenda, agenda-dia, agenda-search, notificacoes, sumidos-google
//   (o hook só mexe no cache; fechar o diálogo e anunciar pelo `resultado` ficam nos callbacks do
//    `mutate`, no EventHeader — o banner desmonta no sucesso)
//   onError com codigo "nao_marcado" | "cancelado": invalidar ["event", id] e a faixa, fechar o diálogo
```

`useRunSync` (admin) e `useSyncEvent` também invalidam a faixa e o sino no sucesso.

## Textos fixos

| Onde | Texto |
|---|---|
| Faixa | `1 evento sumiu do Google Agenda` / `N eventos sumiram do Google Agenda` (N = `total`). Um evento: a barra é link e, a partir de `sm`, mostra ` — <título> · dd/mm/aaaa` (ou `sem data`). Vários: a frase abre a lista; cada linha é título + `dd/mm/aaaa` (ou `sem data`); se `total` passar dos itens recebidos, última linha `e mais N`. |
| Selo na agenda | componente `SeloSituacao` (o tipo é `SituacaoEvento`), ícone `CalendarX` — o mesmo do aviso do sino. `Sumiu do Google` (tooltip: `Sumiu do Google Agenda — percebido em dd/mm/aaaa`). O tooltip é o atributo `title` — complemento de ponteiro; em toque, a data é lida no banner do evento. No chip do Mês e no bloco curto do Dia vai só o ícone (R10). |
| Portal | `Evento em confirmação — entre em contato com a produção` |
| Banner, para todos que abrem o evento | `Sumiu do Google Agenda — percebido em dd/mm/aaaa. O evento continua valendo no sistema.` e `O que for editado aqui fica só no sistema e vai ao Google Agenda quando o Superadmin devolver o evento.` (sem dinheiro, sem botão, sem motivo) |
| Banner, para o Superadmin | `O cancelamento com devolução do dinheiro chega na próxima entrega. Se este evento foi cancelado de verdade, ele fica marcado até lá.` |
| Banner, para o Comercial | `A decisão é do Superadmin — conte a ele por que o evento saiu do Google Agenda.` — aparece só para quem tem `flags.can_request_delete` e não tem `flags.can_delete` |
| Banner, satélite | `Venda do grupo — os valores estão no evento principal` (com link para o principal) |
| Banner, "O evento já foi recriado à mão no Google?" | `1. Acerte neste evento a data, o horário e o local que valem agora — a devolução usa o que está no sistema. 2. Abra o evento que foi recriado, tire dele o que foi lançado em duplicidade (venda, comprovantes, contrato, escala) e só então apague-o no Google Agenda — se for apagado com algo dentro, ele também fica marcado. 3. Devolva este evento ao Google Agenda — é ele que guarda os comprovantes, o contrato e a escala.` |
| Menu, "Excluir ou cancelar" desabilitado, e botão "Analisar e decidir" desabilitado (`title`) | `Este evento sumiu do Google Agenda — por enquanto só pode ser devolvido. O cancelamento chega na próxima entrega.` |
| Diálogo | título `Devolver ao Google Agenda?`; botão de confirmar `Devolver ao Google Agenda`; `Será recriado como: <título> — <data e horário>` (sem data: `sem data`, e o servidor recusa com a mensagem de `sem_data`, mostrada dentro do diálogo); quando a data passou: `Esta data já passou — se o evento mudou de dia, edite a data antes de devolver.`; `Ele volta sem convidados — os convites por e-mail não são reenviados. Ensaios que também foram apagados do Google não voltam.` |
| Diálogo, `<data e horário>` | no mesmo dia, com horário — `19/09/2026 15:00 — 18:00`; dia inteiro (início e fim à meia-noite e fim maior que o início, a regra do `all_day` da R13) — `19/09/2026 (dia inteiro)` ou, em vários dias, `19/09/2026 a 21/09/2026 (dia inteiro)`, com o último dia inclusivo; com horário terminando em outro dia — `19/09/2026 22:00 — 20/09/2026 02:00`. Não reusa o `formatRange` do cabeçalho, que mostra `00:00 — 00:00` e perde o dia do fim. |
| Diálogo, "já passou" | quando o fim do evento (ou o início, se não houver fim) é anterior a agora. Evento de hoje ainda não terminado e dia inteiro de hoje não recebem o aviso. |
| Depois de devolver (linha `aria-live` do cabeçalho) | `recriado`: `Evento devolvido ao Google Agenda.`; `reapareceu`: `O evento já estava de volta no Google Agenda — a marca foi retirada.` |
| `/admin/sync`, confirmação (`ConfirmDialog`, no lugar do `window.confirm` de hoje — Princípio V) | título `Limpar eventos fantasma?`; texto `O sistema confere no Google Agenda cada evento que não aparece na lista do mês, em todos os meses que têm evento no banco. Evento vazio que sumiu é removido. Evento com venda, comprovante, contrato, escala ou grupo fica e é marcado. Evento que só mudou de data é atualizado.`; botão `Limpar` |
| `/admin/sync`, resultado (`message`) | `Limpeza concluída em M mês(es): R removido(s), K mantido(s) e marcado(s), D com data atualizada, V de volta ao Google Agenda, I sem confirmação do Google, F com falha.` Quando algum mês não pôde ser consultado, a mensagem termina com ` E mês(es) com erro.` Abaixo da mensagem, a tela lista uma linha por mês de `results[]` que tenha algum número diferente de zero, e o mês com `ok` falso por erro de consulta aparece como `AAAA-MM: não foi possível consultar o Google Agenda`; com falha, sem confirmação ou mês com erro, a caixa usa o tom de alerta em vez do de sucesso. |
| Resumo do ciclo automático (`detail` do `sync_ok`/`sync_erro`), antes da lista de meses, sempre presente | `Sumiços: M marcado(s), D com data atualizada, V de volta ao Google Agenda, I sem confirmação, F com falha.` |
| Histórico do evento — marcar | `Sumiu do Google Agenda — mantido no sistema. Preso: <descrição>. Aviso enviado a N pessoa(s).` |
| Histórico do evento — reaparecer | `Reapareceu no Google Agenda — a marca "Sumiu do Google Agenda" de dd/mm/aaaa foi retirada.` |
| Histórico do evento — devolver | `Devolveu o evento ao Google Agenda (estava marcado "Sumiu do Google Agenda" desde dd/mm/aaaa).`; no ramo "já tinha voltado": `Devolveu o evento ao Google Agenda: ele já estava de volta e nada foi criado (estava marcado "Sumiu do Google Agenda" desde dd/mm/aaaa).`; quando a origem muda (FR-044), acrescenta ` O elenco deste evento passa a ser mantido pelo sistema: personagem acrescentado no título pelo Google não cria vaga.` |
| Avaliação de evento cancelado (portal) | `Este evento foi cancelado e não recebe avaliação.` |
