# API Contracts — Feature 235: EducaManto por responsabilidades

Todos os endpoints exigem sessão autenticada. Papéis: `_CAN_USE` = {COMERCIAL, SUPERADMIN, ENSAIO, REVENDEDOR_EDUCAMANTO}; gestão de musicais = SUPERADMIN (ver = COMERCIAL + SUPERADMIN). Envelope de erro: `json_error` padrão do projeto.

## GET /api/educamanto/musicals

Papéis: `_CAN_USE`. Lista para o dropdown da calculadora.

```jsonc
{ "musicals": [ { "id": 1, "name": "Uma Aventura Animal",
    "num_personagens": 9, "num_producao": 2, "num_ensaios": 2 } ] }
```

`GET /api/educamanto/musicals/<id>` devolve o musical completo (margens, custos por cenário, itens) **apenas para SUPERADMIN** — coerente com FR-028. COMERCIAL vê a listagem de gestão sem custos/margens (nomes, equipe, nº de ensaios). Custos/margens **nunca** vão no payload da listagem da calculadora.

## POST /api/educamanto/calcular

Papéis: `_CAN_USE`. Calcula **uma** configuração (a tela chama por página, com debounce).

Request:

```jsonc
{
  "musical_id": 1,
  "d1": 1, "d2": 0, "ensemble": 2,
  "responsabilidades": { "som": "manto", "iluminacao": "contratante",
                          "alimentacao": "manto", "cenario": "manto" },
  "fora_sp": false, "km_ida": null,        // km_ida obrigatório quando fora_sp=true (>0)
  "acrescimo": 500.0,
  "contratacao_manto": {                    // opcional
    "duracoes": ["1h", "2h"],              // não-vazio quando presente
    "payload": { /* mesmo shape do POST /api/orcamento/calcular, sem nota_fiscal/fora_sp */ }
  }
}
```

Response 200 — **todos os papéis**:

```jsonc
{
  "scenario": "1 sessão — 1 dia",
  "headcount": 13,
  "tecnicos": ["sonoplasta", "tecnico_som"],
  "transporte": { "modo": "caminhao_sp" | "vans_fora_sp", "total": 800.0,
                   "detalhe": "R$ X por viagem × N dias" },       // detalhe só fora de SP
  "valor_final_sem_nota": 15400.0, "valor_final_com_nota": 18400.0,
  "a_vista_sem_nota": 14630.0, "a_vista_com_nota": 17480.0,
  "acrescimo_efetivo": 500.0, "acrescimo_maximo": 15400.0, "acrescimo_capado": false,
  "desconto_aplicado": false,
  "combinados": { "1h": { "sem_nota": 18600.0, "com_nota": 22200.0,
                            "a_vista_sem": 17670.0, "a_vista_com": 21090.0 } }  // se contratação
}
```

Adicional **apenas superadmin** (removido no servidor para os demais — não é omissão de UI):

```jsonc
{
  "breakdown": {
    "item_rows": [ { "name": "...", "qty": 3, "raw": 1200.0, "sell": 1692.0 } ],
    "raw_cost": 10363.0, "valor_base": 14611.83, "desconto": 0.0,
    "blocos": { "som": 4000.0, "iluminacao": 0.0, "cenario": 900.0, "alimentacao": 715.0 },
    "contratacao_memoria": [ /* memoria do calculate_quote */ ]
  }
}
```

Erros 400: musical inexistente; `d1 + d2 <= 0`; `fora_sp` sem `km_ida > 0`; contratação com `duracoes` vazio.

## POST /api/educamanto/orcamento/gerar

Papéis: `_CAN_USE`. Recebe **as entradas** de todas as configurações + `client_name`, `event_date`, `observacao`. O servidor **recalcula tudo** (nunca aceita valores prontos do cliente), grava o snapshot v2 e devolve o PDF (`application/pdf`, attachment `orcamento-educamanto-<id>.pdf`).

```jsonc
{ "configs": [ { /* mesmo shape do request de /calcular */ } ],
  "client_name": "Colégio X", "event_date": "2026-09-12", "observacao": "..." }
```

Erros 400: nenhuma configuração; qualquer configuração inválida (mesmas regras do /calcular, indicando o índice da página: `{"field": "configs[1].km_ida", ...}`).

## GET /api/educamanto/historico · GET /api/educamanto/historico/<id> · GET /api/educamanto/orcamento/<id>/pdf

Como hoje (filtros, snapshot congelado, PDF inline), com duas mudanças: o detalhe devolve snapshot v1 **ou** v2 (campo `version`), e para papéis não-superadmin os resultados vêm sem breakdown (mesmo corte do /calcular).

## CRUD de musicais (substitui /packages)

- `GET /api/educamanto/musicals` (listagem de gestão, COMERCIAL+SUPERADMIN — margens/custos incluídos **só na resposta do superadmin**)
- `POST /api/educamanto/musicals` · `PATCH /api/educamanto/musicals/<id>` · `DELETE /api/educamanto/musicals/<id>` · `POST /api/educamanto/musicals/<id>/duplicate` — SUPERADMIN.
- Validações: `num_ensaios >= 2` (400 "O mínimo são 2 ensaios."); `name` obrigatório e único; custos ≥ 0.
- Endpoints antigos `/api/educamanto/packages*` são removidos (breaking interno aceito — o frontend migra junto no mesmo deploy).

## Rotas Jinja desligadas (redirects 302)

- `GET /educamanto` (view Jinja) → `/educamanto` React (a rota Flask deixa de renderizar template e passa a redirecionar para o SPA)
- `GET /educamanto/packages*` → `/educamanto/musicais`
- `GET /educamanto/history` → `/educamanto/historico`
- `GET /educamanto/api/distancia` e demais helpers usados pelo template morrem junto (o React usa `/api/educamanto/distancia`).
