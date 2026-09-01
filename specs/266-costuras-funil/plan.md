# Plano de implementação — Feature 266

**Spec**: `spec.md` · **Branch**: `266-costuras-funil` (criada de `main` em `3056faf`)
**Migration**: 1 (aditiva) · **Endpoints novos**: 0 · **Componentes novos em `@manto/ui`**: 0

> Todas as âncoras abaixo foram conferidas no código em 31/08/2026. Onde a premissa original da
> análise estava errada, o plano registra a correção — são quatro, e três delas mudariam o
> resultado se seguidas às cegas.

---

## 1. Restrições que moldam o plano

| Restrição | Consequência |
|---|---|
| `dashboard_service.py` não importa `flask.request` (é serviço, não rota) | os contadores não podem depender de query param; `app/api/dashboard.py` fica intocado |
| `_require_vendas` de formulários lê `current_user.roles` **cru** | não serve para a Home: ignora impersonação. O gate é `show_comercial` do dashboard |
| `staleTime: 30_000` + `refetchOnWindowFocus: false` | invalidação faltante **não se conserta sozinha** — o número errado fica na tela |
| Nenhum módulo novo em `app/api/` | nada a registrar em `app/api/__init__.py` |
| `start_at` / `sale_date` são horário de parede naive | qualquer recorte de data é `.slice(0,7)`, **nunca** `new Date()` |

## 2. Ordem de implementação

O item 1 é pré-requisito de 2 e 3 (sem ele os links caem na lista sem abrir o diálogo). O resto é
independente e paralelizável.

```
 A. verify_266.py (Princípio VIII — antes do código)
 B. migration da coluna client_link_source
 ├─ 1. deep-link ?resposta=  ──┬─ 2. link evento → resposta
 │                             └─ 3. link ficha → resposta
 ├─ 4. link evento → cliente
 ├─ 5. link evento → talento (2 cards)
 ├─ 6. card Avaliações na ficha
 ├─ 7. botão "Criar evento" no resultado do orçamento
 ├─ 8. auto-associação de cliente + client_link_source
 ├─ 9. source="formulario" (2 edições, indivisíveis)
 ├─10. e-mail de resposta nova
 └─11. card Formulários na Home (+ relógio + invalidação)
```

## 3. Backend

### B. Migration — `form_responses.client_link_source`

`down_revision = "e08e454c4780"` (head atual — confirmar com `flask db heads`).
`op.add_column("form_responses", sa.Column("client_link_source", sa.String(20), nullable=True))`.
Espelha `event_link_source`. Sem backfill: linha antiga com `client_id` preenchido fica `NULL`, que
lê corretamente como "origem desconhecida (anterior à 266)".

### 8. Auto-associação de cliente por telefone

**Novo** em `formularios_ops.py`, logo após `_attempt_auto_link` (:609):
`_attempt_auto_link_client(response) -> str | None` — mesmo contrato do irmão (type hints, docstring
Google, **sem commit**).

Retorna `None` se `response.client_id` já existe, se `client_link_source` marca decisão humana, ou
se `contact_phone` é vazio. Senão roda a mesma query da sugestão
(`Client.query.filter_by(phone=response.contact_phone).first()`, hoje em
`formularios_admin_read.py:107`), e havendo cliente faz `fill_client_from_response` +
`response.client_id = client.id`, retornando `"auto_phone"`.

Em `formularios_write.py`, dentro do `try` best-effort que já existe (:98-104): chamar a função,
gravar `client_link_source`, e — **só quando o vínculo de evento também ocorreu na mesma passada** —
chamar `ensure_event_client(response.event, response.client_id)`. Condição de commit passa a
`if result or client_result:`. Ampliar a mensagem do `logger.exception` para citar os dois vínculos.

- ⚠️ **Nunca criar `Client`** — endpoint público sem autenticação (decisão 12).
- ⚠️ **Não tocar `retry_auto_link_pending`** (:612-637): o filtro dele é `event_link_locked`, que não
  sabe nada sobre cliente — religaria a cada ciclo de sync o vínculo que a comercial desfez
  (decisão 11).
- `associate_client` passa a gravar `"manual"`; `dissociate_client` (:246-249) passa a zerar
  `client_link_source` junto com `client_id`.
- Efeito esperado na tela: `suggested_client` só é calculado quando `client_id is None`
  (`formularios_admin_read.py:105-107`), então a caixa de sugestão **para de aparecer** nas respostas
  novas. É o comportamento correto — mas alguém vai reportar como "sumiu a sugestão".
- `client_link_source` precisa entrar em `_response_summary` (`formularios_admin_read.py:36-53`)
  **e** no tipo `FormResponseSummary` (`lib/formulariosAdmin.ts:4-19`) para a tela poder exibir a
  origem.

### 8b. `delete_client` solta as respostas — correção obrigatória junto do item 8

`client_ops.py:232-237` limpa `EventClient` e `CalendarEvent.client_id`, mas não
`FormResponse.client_id`. Diferente do vínculo de evento, `FormResponse.client` **não tem backref**
(`models.py:1898`), então o SQLAlchemy não emite o UPDATE de nulificação: a FK
`fk_form_responses_client_id` (sem `ondelete`) estoura `IntegrityError`.

Acrescentar antes do `db.session.delete(client)`:

```python
FormResponse.query.filter_by(client_id=client.id).update(
    {"client_id": None, "client_link_source": None}
)
```

⚠️ **Isto não é escopo extra — é a consequência direta do item 8.** Hoje o caminho é raro (só
associação manual); com a auto-associação ele vira comum. Fechar depois seria entregar uma feature
que quebra a exclusão de clientes.

### 9. `source="formulario"` — duas edições indivisíveis

1. `formularios_ops.py:234` — `source="manual"` → `source="formulario"`.
2. `client_ops.py:200` — incluir a chave no mapa:
   `{"whatsform_import": "formulario", "formulario": "formulario", "kommo_import": "kommo"}`.

⚠️ **Fazer só a (1) deixa a mudança 100% invisível**: `source_keys.get(source, "manual")` tem
fallback silencioso e jogaria o valor novo no balde Manual. Atualizar também o comentário de
`models.py:1823` com a lista real de valores. Sem migration — `source` é `String(20)` livre, sem
Enum nem CHECK.

`useAssociateClient` (`formulariosAdmin.ts:82-92`) passa a invalidar também a chave das métricas de
clientes, senão `/clientes` fica com o número velho.

### 10. E-mail de resposta nova

Nova `send_form_response_email` em `app/email_service.py` usando os helpers de layout já prontos
(`_html_wrap`/`_info_row`, :74-156), disparada por `send_async` no fluxo do POST público.
Destinatários: usuários ativos com papel `COMERCIAL` ou `SUPERADMIN` (validação de destinatários
internos no padrão de `audit_agent.py:105-117`).

Idempotência não precisa de tabela: o envio está no caminho do POST, que roda uma vez por resposta.
Falha de SMTP é engolida por `_send` (:843-861) e não altera o 201 (decisão 7).

### 11. Card na Home — backend

Em `dashboard_service.py`, após o bloco `comercial` (:538):

```python
show_formularios = show_comercial  # COMERCIAL ∪ FINANCEIRO ∪ SUPERADMIN == _require_vendas
formularios: dict[str, Any] | None = None
if show_formularios:
    from app.formularios import formularios_ops   # import local, padrão do arquivo
    formularios = formularios_ops.count_status()
```

Variável própria (e não reuso direto de `show_comercial`) para os gates poderem divergir depois sem
ninguém se perder. `count_status()` já devolve os 5 inteiros em **uma** query. Acrescentar
`"formularios": formularios,` ao dict de retorno (:580-591).

**Relógio, no mesmo commit:** `formularios_ops.py:145` usa `date.today()` → `now_sp().date()`
(`from app.constants import now_sp`). Em UTC, entre 21h e meia-noite de SP a festa de **hoje** sai da
contagem — hoje o erro vive numa tela interna; sem a correção ele passa a morar na primeira tela do
sistema. *Não* mexer em `dashboard_cutoff` nem `resolve_performance_period` (mesmo defeito, fora de
escopo — só não replicar o padrão no código novo).

## 4. Frontend

| # | Arquivo | Mudança |
|---|---|---|
| 1 | `pages/FormulariosAdminPage.tsx` | `useSearchParams` no lugar do `useState` de `selected` (:668); `abrirResposta`/`fecharResposta` copiando `new URLSearchParams(searchParams)` (padrão `Tags3DPage.tsx:64-69`); passar em `:774` e `:780` |
| 2 | `components/EventDetail/ComercialSection.tsx` | link no `DataRow` (:434, ramo **somente-leitura**) **e** linha "Ver resposta completa" abaixo do `FormResponsePicker` (:447-455, ramo editável) |
| 3 | `pages/ClientDetailPage.tsx` | `<span>{f.form_type_label}</span>` (:220) → `<Link to={/formularios?resposta=${f.id}}>` |
| 4 | `components/EventDetail/ComercialSection.tsx` | `<span>{client.name}</span>` (:413) → `<Link to={/clientes/${client.client_id}}>`, mantendo `<span>` quando o nome é nulo |
| 5 | `components/EventDetail/CastingSection.tsx` | `import { Link }` (novo no arquivo); link no avatar (:227, com `aria-label` e `className="flex-none"`) e no nome (:266) — **e o mesmo no `PresencaCard`** (:173-187) |
| 6 | `pages/ClientDetailPage.tsx` | componente local `AvaliacoesCard` usando `useClientFeedback({ period: "all", client_id })` — hook e endpoint **já existem** |
| 7 | `pages/OrcamentoResultadoPage.tsx` | 4º botão na barra `actions` (:180) → `/events/new?orcamento_id=${entryId}`, variante sólida |
| 11 | `lib/types.ts` · `pages/DashboardPage.tsx` · `lib/formulariosAdmin.ts` | tipo + `SectionKey` + stat + painel + guarda do "Tudo em dia!" + invalidação de `["dashboard"]` |

### Correções de premissa (não seguir a análise às cegas)

1. **Item 2 é em dois lugares.** O `DataRow` do pré-contrato só renderiza sob `if (!canEdit)`; com
   permissão de edição — o caso normal do comercial — quem desenha o vínculo é o
   `FormResponsePicker`, que não tem link. Mexer só no `DataRow` deixaria justamente o comercial sem
   o link.
2. **O id do talento é `role.talent.id`, não `role.talent_id`** — este campo não existe em
   `RoleItem`. `role.talent` é anulável; o guarda é obrigatório.
3. **`AvatarThumb` é decorativo** (`aria-hidden`, `alt=""`): um `<Link>` só em volta dele é anunciado
   como link vazio. `aria-label` explícito, e `flex-none` no link ou o flexbox comprime o avatar.
4. **`useClientFeedback` não tem `enabled`.** Com `:id` inválido, `if (filters.client_id)` é falso
   para `NaN`, o parâmetro some da query e o card mostraria **todas as avaliações da empresa** na
   ficha de uma cliente. Renderizar o card só dentro do bloco `{query.data && …}` e/ou acrescentar
   `enabled` ao hook.

### Detalhes que quebram em silêncio

- **Parse do `?resposta=`**: `Number("abc")` é `NaN` e `enabled: id != null` continua verdadeiro → a
  query vai para `/api/formularios/respostas/NaN`, que não casa com o conversor `<int:...>` do Flask
  e devolve **404 HTML**, não o envelope `json_error`. O `apiFetch` estoura no `JSON.parse`. Filtrar
  para inteiro positivo antes de passar adiante.
- **`setSearchParams` com objeto literal apaga os outros parâmetros.** Sempre
  `new URLSearchParams(searchParams)` + `set`/`delete`.
- **Fechar limpa o parâmetro inclusive na exclusão** (`del.mutate(id, { onSuccess: onClose })`,
  :594): senão um F5 depois de excluir reabre o diálogo num id morto.
- **`propsSecao` é tipado por `SectionKey`** — sem a chave nova no union o `tsc` reprova; e sem o
  `<div {...propsSecao("formularios")}>` o clique no stat abre o painel mas não rola até ele.
- **O painel entra DENTRO da grid** (`DashboardPage.tsx:664`, fecha em :882), senão vira faixa de
  largura total e quebra o ritmo de duas colunas.
- **Guarda do "Tudo em dia!"** (:884-890) precisa de `!data.formularios &&`, senão o card de vazio
  aparece junto com o painel novo.
- **Contagem não é dinheiro** — nada de `formatBRL`; usar `tabular-nums`.

## 5. Verificação

`verify_266.py` contra `manto_local` via `.\scripts\db\run-local.ps1`, **escrito antes do código**.
Cobertura na spec §Verificação. Dois pontos de método que a feature 257 ensinou:

- o teste de escrita confere por **conexão separada** — o autoflush da própria sessão esconde
  ausência de commit;
- o teste de RBAC confere **ausência de chave** no payload, não status 403 — é assim que o dashboard
  expressa permissão.

Ensaio da migration num banco descartável com o `startCommand` inteiro antes do merge.

## 6. Riscos

| Risco | Mitigação |
|---|---|
| Auto-associação vincular ficha errada (telefone compartilhado) | `client_link_source="auto_phone"` deixa rastro; comercial troca pela tela |
| "Sumiu a sugestão de cliente" reportado como bug | é consequência esperada; registrar em `docs/03` |
| Card da Home com número errado por relógio UTC | corrigido no mesmo commit (§3.11) |
| Card da Home desatualizado após ação em `/formularios` | invalidação de `["dashboard"]` por prefixo |
| `ensure_event_client` elege contratante a partir de envio anônimo | só quando o vínculo de evento também ocorreu; paridade com `link_event` (decisão 13) |

## 7. Fechamento do ciclo

`docs/01` (chave nova no contrato de `GET /api/dashboard` + coluna nova), `docs/02` (painel da Home,
deep-link `?resposta=`, card de avaliações, novos vínculos entre telas), `docs/03` (entrada no topo).

Aproveitar para corrigir as três referências mortas encontradas na análise: auto-vínculo apontado
para `app/formularios/routes.py:246` (arquivo removido) em `docs/00:68` e `docs/04:396`; "4 threads
de background" quando há 7; e as três armadilhas de `docs/04` §1 já resolvidas pelas features
246 e 253.
