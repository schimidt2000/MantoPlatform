# Contrato de endpoints (Phase 1) — Feature 301

**Spec**: [spec.md](../spec.md) · **Plano**: [plan.md](../plan.md) · **Data**: 2026-09-21

> ⚠️ **Leia isto antes de reescrever qualquer um destes endpoints.**
>
> Esta feature existe porque um arquivo como este descreveu a regra errada. Em 23/07/2026 o
> contrato da feature 177 (`specs/177-migracao-ferramentas-react/contracts/api-endpoints.md:119`)
> registrou *"SUPERADMIN vê de todos os usuários, demais só o próprio (mesma regra de `is_sa` em
> `routes.py:714`)"* — mas naquele dia `routes.py:714` **já não tinha** esse filtro; ele tinha sido
> removido de propósito em 20/05 (`6b191e4`). O contrato descreveu código de dois meses antes, e a
> migração para React implementou o contrato fielmente. A regressão durou **dois meses** e se
> espalhou para outras duas superfícies, as duas no domínio Agenda/evento.
>
> **A regra desta página é a regra vigente.** Se a próxima reescrita discordar dela, confira o
> código **e** `docs/01` §4.3 antes de copiar qualquer coisa daqui — e atualize os dois.

**Nenhum endpoint novo.** **Sete** endpoints mudam de comportamento — cinco do histórico e dois de
evento; nenhum muda de rota, método ou gate. E os sete **não** compartilham o mesmo gate: os de
evento têm gate próprio, mais largo, que já aceita FINANCEIRO (ver cada seção).

---

## Regra única, em uma frase

**O gate de módulo não muda. A checagem de dono morre na leitura, sobrevive no `DELETE`, e no
vínculo passa a olhar o orçamento já vinculado — nunca o alvo.**

---

## Orçamento — histórico

Gate de módulo em todos: `_require_vendas()` de `app/api/orcamento_read.py` —
**COMERCIAL** ou **SUPERADMIN**. FINANCEIRO leva **403** (é o homônimo já marcado em `docs/01`
§4.3 como "regra diferente"; não confundir com o `_require_vendas()` de `clientes_read.py`, que
aceita FINANCEIRO). **Inalterado por esta feature.**

### `GET /api/orcamento/historico`

- **Dono**: nenhuma checagem. Todos os autorizados veem os orçamentos de todos (FR-001).
- **Escopo inicial**: sem filtro pré-aplicado — a lista abre com o time inteiro (FR-012).
- **Query** (inalterada): `q`, `date_from`, `date_to`, `min_val`, `max_val`, `has_show`, `user_id`.
  `user_id` deixa de ser privilégio de superadmin e passa a valer para qualquer autorizado (FR-005).
- **Limite**: 300 linhas, `created_at DESC`. Mantido de propósito (decisão do clarify); ver R8.

**200**:

```json
{
  "entries": [{
    "id": 0, "created_at": "", "client_name": "", "event_location": "", "event_date": "",
    "total_1h": 0, "total_2h": 0, "total_3h": 0, "total_4h": 0, "has_show": false,
    "user_name": "",
    "event_id": null, "event_title": null,
    "pode_excluir": false
  }],
  "users": [{"id": 0, "name": ""}]
}
```

| Chave | Mudança | Por quê |
|---|---|---|
| `pode_excluir` | **nova**, por linha | `true` se o autor é quem pede, ou se é SUPERADMIN. O React esconde "Excluir" por esta chave e **nunca** comparando ids (Princípio XIII, FR-007) |
| `users` | **sempre populada** | alimentava só o superadmin; agora alimenta o seletor de vendedor de todo mundo (FR-005) |
| `is_superadmin` | **REMOVIDA** | existia só para três `if` de tela que agora são incondicionais. Deixá-la viva é deixar a alavanca que espalhou a regressão. Leitor único **da chave** — o endpoint tem três consumidores (R5) |
| `user_name` | inalterada | já vinha no payload; passa a ser **exibida** para todos (FR-004) |

> **Outros dois consumidores, fáceis de esquecer**: `OrcamentoPicker.tsx:29` (a busca de orçamento
> da aba Comercial do evento) usa **este mesmo endpoint** com `?q=` — é por ele que FR-011 vira
> ação real na tela, e a linha do resultado precisa passar a mostrar `user_name` (R6). E
> `OrcamentoCalculadoraPage.tsx:120` chama sem filtro só para contar: o selo ao lado do link
> "Histórico de Orçamentos" (`:508-511`) passa a contar o time e **satura em 300** — efeito aceito,
> registrado nos Casos de borda da spec.

### `GET /api/orcamento/historico/<id>`

- **Dono**: **nenhuma** checagem (FR-002). Abre o de qualquer pessoa.
- **200**: `{"quote": {...}, "form_snapshot": {...}}` — inalterado. `form_snapshot` é o que
  alimenta "Recalcular"; registro legado continua passando pelo fallback de `quote_ops`.
- **404**: só quando o orçamento **não existe**. Nunca mais "não encontrado" para orçamento de
  outra pessoa (FR-010).

### `GET /api/orcamento/historico/<id>/pdf`

- **Dono**: **nenhuma** checagem (FR-003). **200**: PDF binário. Sem registro de auditoria.

### `POST /api/orcamento/historico/<id>/enviar-email`

- **Dono**: **nenhuma** checagem (FR-003).
- **Body**: `{"to"?}` — inalterado. **200**: `{"sent": true}` · **400** e-mail inválido ·
  **502** falha no envio.
- **Auditoria (FR-013)**: quando o orçamento é **de outra pessoa** e o envio **deu certo**, grava
  uma linha em `AuditLog` com quem enviou, qual orçamento e para qual endereço.
  - Reenvio do próprio orçamento: **não** grava.
  - Envio que falhou: **não** grava.
  - **O endpoint precisa commitar**: `audit()` só faz `add` (`app/utils.py:46`). Hoje esta view não
    commita nada — sem o commit, a linha morre no fim da requisição (hotfix 257).

### `DELETE /api/orcamento/historico/<id>`

- **Dono**: **MANTIDA** (FR-006). Só o autor ou o SUPERADMIN. É a única trava de dono que sobrevive
  no módulo, e é decisão explícita de `6b191e4`, tomada no mesmo commit que liberou a visualização.
- **409 + `event_id`** (feature 273) continua valendo enquanto houver evento vivo vinculado, mas
  vem **depois** da checagem de dono, não antes: em `orcamento_write.py` o dono é resolvido dentro
  de `_get_entry_para_excluir` (404) e `outro_evento_vivo_do_orcamento` só algumas linhas abaixo. Quem não é o autor leva 404 e nunca
  chega no 409. **Não reordenar** — o 409 carrega o `event_id`, então antecipá-lo confirmaria a
  existência do orçamento e do evento para quem não é autor (Princípio XIII: 404, não 403).
- **Armadilha de implementação**: os quatro endpoints acima e este compartilham hoje
  `_get_entry_or_none(entry_id, is_sa)`. Soltar a trava na função solta **também o `DELETE`**. A
  função se divide em duas, com nomes que dizem a regra (R1).

---

## Evento

### `GET /api/events/<id>` — bloco `venda`

- **Gate**: COMERCIAL, FINANCEIRO, SUPERADMIN (`show_comercial`) — inalterado.
- **Dono**: o comercial deixa de precisar ser o autor para receber o bloco (FR-009). FINANCEIRO
  **continua** sem o orçamento (não tem o módulo) e continua recebendo `tem_orcamento`.

```json
{"venda": {"orcamento": {
  "id": 0, "client_name": "", "event_date": "", "event_location": "",
  "fora_sp": false, "km_ida": 0, "deslocamento_cliente": false,
  "coordenador_qty": 1, "maquiagens": 0, "cantores": 0, "personagens": [],
  "has_show": false, "total_1h": 0, "total_2h": 0, "total_3h": 0, "total_4h": 0,
  "autor": "",
  "pode_gerir": false
}}}
```

| Chave | Origem | Por quê |
|---|---|---|
| `autor` | `resumo_do_orcamento` (`_ops` puro) — é dado do orçamento | sem o nome, a recusa não cumpre FR-010 ("dizer quem pode agir"). **Não** se chama `vendedor`: o mesmo bloco `venda` já traz `venda.seller`, o vendedor **do evento** — que pode ser outra pessoa. Autor sem nome recordável: a chave traz `"Vendedor não identificado"`, e a trava continua no `user_id`, nunca no nome |
| `pode_gerir` | **a view** (`agenda_read.py`) — é RBAC, não cabe no `_ops` (Princípio III) | `true` se quem pede é o autor do orçamento vinculado, ou SUPERADMIN |

> **Por que `pode_gerir` é obrigatório e não cosmético**: `ComercialSection.tsx:580` hoje deduz
> "orçamento de outro" de `!orc && venda.tem_orcamento` — *"o servidor não me deu, logo não é meu"*.
> Com FR-009 o servidor **sempre** dá, então essa dedução vira `false` para sempre e o aviso
> **sumiria exatamente quando o servidor passa a recusar**: a pessoa veria "Aplicar", "Trocar" e
> "Desvincular", clicaria, e levaria erro. Trocar dedução por flag não é limpeza — é o que impede a
> feature de criar um botão mentiroso.

### `PATCH /api/events/<id>/orcamento`

- **Gate**: `_can_manage_sale()` — COMERCIAL, FINANCEIRO, SUPERADMIN. **Inalterado.**
- **Body** (inalterado): `{"orcamento_history_id": int|null, "aplicar_equipe"?: bool (padrão
  **true**), "aplicar_valores_duracao"?: 1|2|3|4, "sale_date"?: "AAAA-MM-DD"}`. `null` desvincula.
  `aplicar_equipe` é a forma que a tela mais usa: "Aplicar ao evento"
  (`ComercialSection.tsx:560`) manda `{orcamento_history_id, aplicar_equipe: true}` e mais nada.
  Ao contrário dos vizinhos, essa chave **não** valida tipo — passa por `bool(...)`.
  O que ela faz é **acrescentar o que falta**, nunca reescrever: `is_outside_sp` só sobe para
  `true` (nunca rebaixa), `travel_distance_km` só é gravado se o evento ainda não tiver, e os
  papéis de apoio só nascem se o orçamento os vendeu e o evento não os tem. É por ser idempotente
  que o cenário 9 do verify exige um arranjo onde ainda haja algo a escrever (spec, §Verificação).

**A regra, pelo estado do evento** (FR-011):

| Evento está… | Ação pedida | Quem pode |
|---|---|---|
| **sem** orçamento vinculado | vincular qualquer orçamento | **COMERCIAL ou SUPERADMIN** — o 404-por-dono sobre o **alvo** morre para quem tem o módulo de Orçamento; FINANCEIRO passa no gate mas segue no 404 |
| vinculado a orçamento **meu** | trocar · desvincular · re-aplicar | eu (inalterado) |
| vinculado a orçamento **de outro** | trocar · desvincular · **re-aplicar** | só o autor dele ou SUPERADMIN → **409** |

- **404**: duas causas, e o cliente não as distingue de propósito — (a) o orçamento alvo **não
  existe**; (b) quem pede **não tem o módulo de Orçamento** (FINANCEIRO) e apontou orçamento que
  não é dele. A segunda é o que impede a feature de alargar o acesso do FINANCEIRO (SC-005).
- **409 `orcamento_de_outro`**: a mensagem passa a **nomear o autor** e a dizer que só ele ou o
  superadmin podem mexer (FR-010).
- **409 `OrcamentoJaVinculado`**: inalterado — o orçamento já está em outro evento vivo.

> **O vão que esta feature fecha, e que não existia como bug visível**: quando `orcamento_history_id`
> do body é **igual** ao vínculo atual (re-aplicar sem trocar), a guarda de 409 de hoje não dispara
> — `atual_id != entry.id` é falso. Isso nunca vazou porque o 404 do alvo barrava antes. Ao remover
> o 404, **re-aplicar ficaria aberto** e reescreveria `sale_value` e `sale_date` de uma venda
> alheia — e `sale_date` decide o mês em que a comissão cai na planilha (hotfix 267b). Por isso a
> guarda é **reescrita**, não relaxada. Cenário 9 do `verify_301.py` existe exatamente para isto,
> e **deve falhar**.

---

## Endpoints que NÃO mudam (conferidos, para ninguém "consertar" por tabela)

| Endpoint | Situação |
|---|---|
| `GET /api/events/new/prefill` | **nunca** teve checagem de dono — já dá para criar evento a partir do orçamento de qualquer pessoa. Fica como está; é uma das provas de que a trava era acidental |
| `GET /api/educamanto/historico` e detalhe | **já** mostram tudo para todos; a regressão nunca chegou lá. Não tocar (inclusive o corte do custo interno do caminhão para não-superadmin) |
| `GET/POST /api/orcamento/settings*` | exclusivos do SUPERADMIN. Inalterados |
| `GET /api/orcamento/{opcoes,personagens-no-dia,distancia}` | sem noção de dono. Inalterados |
| `POST /api/orcamento/{calcular,salvar}` | salvar continua gravando `user_id = current_user.id`; "Recalcular" sobre orçamento alheio cria um **novo**, do próprio usuário, e nunca sobrescreve |
| `GET /api/financeiro/comissoes`, `/api/vendas/pipeline`, Gastos Extras | escopam por pessoa **por decisão registrada** (013, 179, 187, 196), não por regressão. Fora de escopo |
