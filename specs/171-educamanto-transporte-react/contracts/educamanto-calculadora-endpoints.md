# Contract: Calculadora EducaManto — Endpoints (171)

Convenção geral: `specs/144-migracao-react-spa/contracts/api-conventions.md`.

**Auth (todos os endpoints)**: sessão válida + papel em
`{COMERCIAL, SUPERADMIN, ENSAIO, REVENDEDOR_EDUCAMANTO}` — paridade com `_CAN_USE` já existente em
`app/educamanto/routes.py`, reimplementado como função (não decorator) na API, igual ao padrão das
demais fatias. Sem esse papel → 403.

## `GET /api/educamanto/packages`

Lista os pacotes para o seletor da calculadora — mesmo dado que `EducaMantoPackage.to_dict()` já
produz para o template Jinja (`packages_json`).

- **200**:

```json
{
  "packages": [
    {
      "id": 1,
      "name": "Uma Aventura Animal",
      "margin_1s": 1.41,
      "margin_2s": 1.70,
      "margin_1s_days": 1.50,
      "margin_2s_days": 1.80,
      "discount_days": 2,
      "discount_pct": 0.05,
      "commission_rate": 0.05,
      "ensemble_1s": 350,
      "ensemble_2s": 600,
      "ensemble_1s_days": 300,
      "ensemble_2s_days": 550,
      "items": [
        { "id": 10, "name": "Cara Limpa", "qty": 3, "cost_1s": 400, "cost_2s": 650,
          "cost_1s_days": 350, "cost_2s_days": 600, "ensemble_add": 0 }
      ]
    }
  ]
}
```

## `GET /api/educamanto/distancia?endereco=`

Distância até o endereço do evento — mesmo cálculo já usado por `GET /educamanto/api/distancia`
(reusa `app.maps.distance_km_ida`). Endpoint próprio na API (em vez de reusar a rota Jinja) porque a
API não deve depender de uma rota que renderiza página.

- **Query params**: `endereco` (string, obrigatório)
- **200**: `{ "km_ida": 42.3 }`
- **400**: `{ "error": "Endereço inválido ou não encontrado." }` (ou mensagem equivalente do serviço
  de mapas) — mesmo texto/condição já usado pela rota Jinja, sem reinventar a mensagem.

## `POST /api/educamanto/calcular`

Calcula o valor do pacote (itens, margens, desconto, ensemble) + transporte (já com o multiplicador
de dias, feature 171) — chama `app/educamanto/pricing_ops.py` (`calcular_pacote`/
`calcular_transporte`/`pessoas_transporte`); não persiste nada.

**Transporte é sempre van com carretinha** (decisão de negócio da feature 080 — não há mais seleção
de tipo/carretinha/carro na tela, nem antes nem depois desta feature) e o número de pessoas é
**derivado no servidor** do item "Catering apresentação" do pacote + ensemble (mesma regra já usada
pela tela Jinja, `pessoas_transporte()`) — o cliente não envia `pessoas`.

- **Body**:

```json
{
  "package_id": 1,
  "d1": 2,
  "d2": 1,
  "ensemble": 0,
  "acrescimo": 0,
  "transporte": { "km_ida": 42.3 }
}
```

  - `transporte` é opcional — se ausente ou `km_ida` \<= 0, o transporte no resultado vem zerado
    (paridade com o comportamento atual: sem endereço calculado, transporte é zero).
  - `d1`/`d2`/`ensemble` são inteiros ≥ 0; `acrescimo` ≥ 0 (mesmo cap ao valor original do pacote já
    aplicado hoje no cliente — feature 080/081 — passa a ser aplicado aqui, no servidor).

- **200**:

```json
{
  "scenario": "2d×1 sessão + 1d×2 sessões",
  "item_rows": [
    { "name": "Cara Limpa", "qty": 3, "raw_1s_days": 1050, "raw_2s_days": 650,
      "raw_item": 1700, "sell_item": 2350.5 }
  ],
  "raw_cost": 12500.0,
  "valor_base": 18400.0,
  "desconto_aplicado": true,
  "desconto": 920.0,
  "transporte": {
    "vt": 300.0, "afsp": 46.53, "valor_viagem": 346.53,
    "dias": 3, "total": 1039.59,
    "label": "Van c/ carretinha", "km_total": 84.6, "pessoas": 11
  },
  "valor_final_sem_nota": 18520.0,
  "valor_final_com_nota": 22050.0
}
```

- **400**: `{ "error": "Pacote inválido." }` (package_id inexistente) ou
  `{ "error": "Preencha os dias (1 e/ou 2 sessões) antes de calcular." }` (`d1 + d2 <= 0`) — mesmas
  validações já feitas hoje no Jinja/JS, agora no backend.
- Todos os valores monetários são `number` (float), nunca string formatada — mesma convenção das
  demais fatias (Princípio VII: a formatação BRL é responsabilidade do frontend via `@manto/money`).
