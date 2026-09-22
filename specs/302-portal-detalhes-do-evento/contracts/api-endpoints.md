# Contrato — Feature 302

**Plano**: [../plan.md](../plan.md) · **Pesquisa**: [../research.md](../research.md) ·
**Data**: 2026-09-22

**Nenhum endpoint novo. Nenhum portão alterado. Nenhuma chave removida.** Três endpoints existentes
ganham campos.

> **Regra de compatibilidade desta entrega** (FR-013a / FR-013b, ver R8): `manto-backend` e
> `manto-frontend` são serviços separados no `render.yaml` e não trocam de contêiner juntos.
> Portanto: **nada sai do payload nesta entrega**, e todo campo novo é **opcional** no TypeScript.
> Quem lê este contrato depois: `history` ainda estar aqui **não** é esquecimento — é a decisão, e
> a remoção é tarefa do ciclo seguinte, registrada em `docs/05`.

---

## `GET /api/portal/agenda`

**RBAC**: talento autenticado (`portal_api_login_required`); "é o dono do recurso" — toda consulta
parte do `talent_id` da sessão e nunca aceita id vindo do cliente. **Inalterado.**

**Resposta** — envelope igual ao de hoje:

```jsonc
{
  "pending_invites": [ /* escalação */ ],
  "upcoming":        [ /* escalação */ ],
  "history":         [ /* escalação — CONTINUA sendo enviado; a tela é que parou de usar */ ]
}
```

**Escalação** — as 16 chaves de hoje, mais **duas**:

```jsonc
{
  "role_id": 1234,
  "event_id": 567,
  "title": "Festa da Ana",
  "start_at": "2026-10-03T16:00:00",
  "end_at": "2026-10-03T20:00:00",
  "location": "Buffet Estação Vai e Vem - R. Santa Justina, 251",
  "character_name": "Coordenador",
  "has_unacknowledged_change": false,
  "change_description": null,
  "cache_value": 300.0,
  "travel_cache": 50.0,
  "cache_total": 350.0,
  "cache_defined": true,
  "payment_status": "nao_pago",
  "has_figurino": true,
  "invite_status": "pending",

  // NOVO — código do modelo, não rótulo pronto (R6). A tela escolhe entre
  // "Personagem:" e "Função:". Mesma convenção de payment_status/invite_status.
  "role_type": "extra",

  // NOVO — null quando não há NADA a mostrar (R1). Presente em pending_invites e
  // upcoming; sempre null em history (R11).
  "before_event": {
    "makeup":    { "time": "14:00", "location": "Manto Produções" },
    "departure": { "time": "15:30", "location": "Manto Produções" },
    "rehearsals": [
      {
        "start_at": "2026-09-30T08:30:00",
        "end_at":   "2026-09-30T11:30:00",
        "location": "R. Olga Camelini, 147 - São João Climaco, São Paulo - SP"
      }
    ]
  }
}
```

### Regras do bloco `before_event`

| Regra | Valor |
|---|---|
| `before_event` | `null` quando `makeup`, `departure` e `rehearsals` estão todos vazios |
| `makeup` | objeto **só se houver `makeup_time`**; `null` caso contrário (R3) |
| `makeup.location` | **traduzido**: `"manto"` → `Manto Produções`, `"local"` → `No local do evento`, outro → verbatim. O código **nunca** aparece no JSON (R4) |
| `departure` | objeto **só se houver `departure_time`**; `null` caso contrário (R3) |
| `departure.location` | o valor gravado, ou `Manto Produções` quando vazio |
| `rehearsals` | **lista, sempre** (`[]` quando não há), ordenada por `start_at` crescente (R2, R12) |
| item de ensaio | `start_at`, `end_at`, `location`. **Sem `description`** — o campo guarda endereço, não observação (R9) |
| ensaio cancelado | excluído |
| ensaio **já realizado** | excluído — o bloco é preparação, e o ensaio cai 2 a 4 dias antes do show, então todo show passa por uma janela em que o ensaio é passado e ele é futuro (FR-004a) |
| ensaio órfão (sem `parent_event_id`) | não pertence a evento nenhum e não aparece |

> **O que o servidor NÃO resolve**: a exibição de um evento que termina no dia seguinte (FR-002a)
> é da tela. O payload manda `start_at` e `end_at` completos, em ISO naive; comparar as datas e
> dizer "no dia seguinte" é trabalho do formatador do portal.

---

## `GET /api/portal/historico`

**RBAC**: inalterado.

**Resposta**: envelope igual (`items` + `totals`). Os itens usam o mesmo serializador, então
ganham `role_type`; `before_event` vem **sempre `null`** (R11). `totals` (`paid`, `pending`,
`overall`, `count`) **não muda**.

---

## `GET /api/portal/events/<event_id>/figurino`

**RBAC**: inalterado — talento autenticado, e a ficha só sai para quem interpreta o personagem ou
coordena o evento. O módulo ganha a **declaração de RBAC no topo** que hoje falta — é o único dos
cinco módulos do portal sem ela, e a forma é a mesma prosa que os outros quatro usam
(constituição XIII).

**Mudança de payload: nenhuma.** A ficha já recebe `title` e `start_at`, e a tela simplesmente não
os desenha — a correção é de frontend.

```jsonc
{
  "event": {
    "id": 567,
    "title": "Festa da Ana",
    "start_at": "2026-10-03T16:00:00",
    // Sem `end_at`: FR-014 pede nome e DATA, não faixa horária. A hora já está no card de onde
    // a pessoa veio; repeti-la aqui seria mais um lugar para divergir.
  },
  "is_coordinator": false,
  "sheets": [ /* inalterado */ ]
}
```

**Ponto de conformidade que NÃO muda aqui**: quem não está escalado recebe **403** com "Você não
está escalado neste evento", o que confirma a existência do evento; o Princípio XIII manda 404.
Decisão registrada do dono: fica como está e vira dívida em `docs/05`. **Não "consertar" de
passagem** — mudaria o texto que o artista lê.

---

## O que os endpoints **não** mudam

- Nenhum campo removido de nenhum payload.
- Nenhum portão, nenhum papel, nenhum código de status alterado.
- `app/api/portal_agenda.py` não muda uma linha: continua só orquestrando.
- Os únicos chamadores de `_role_summary` são `get_agenda` e `get_historico` — conferido por
  varredura no repositório, **não** pelo que as docstrings dizem: várias delas ainda falam de um
  "Jinja legado" do portal que **não existe mais** (ver R14).

## Contrato de desempenho

O número de consultas de `GET /api/portal/agenda` **não pode crescer com o número de escalações**.
O bloco custa **uma** consulta para a agenda inteira, e `selectinload` mata o SELECT-por-escalação
que já existia (R7). O cenário **13b** do verify mede: a contagem com 3 escalações tem de ser igual
à contagem com 5.
