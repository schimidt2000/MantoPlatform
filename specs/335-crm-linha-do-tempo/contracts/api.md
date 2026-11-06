# Contratos — 335 Linha do tempo da ficha e funil das conversas

Erros no envelope de `json_error` (`docs/00` §5).

## `GET /api/conversas/funil` (gate `pode_conversas`: Comercial, Superadmin)

Query: `inicio`, `fim` (`AAAA-MM-DD`, datas de São Paulo; padrão o mês corrente), `canal` (`whatsapp`|`instagram`,
opcional), `campanha` (o nome, `__sem_anuncio__` ou `__desconhecida__`, opcional), `dividir` (`vendedor` padrão |
`campanha` | `canal`).

```json
{
  "periodo": {"inicio": "2026-11-01", "fim": "2026-11-30"},
  "total": 120,
  "etapas": [
    {"chave": "chegou", "rotulo": "Chegou", "quantidade": 120, "sobre_chegou": 100.0, "passagem": null},
    {"chave": "orcamento", "rotulo": "Orçamento enviado", "quantidade": 48, "sobre_chegou": 40.0, "passagem": 40.0}
  ],
  "dividir": "vendedor",
  "grupos": [
    {"chave": "12", "rotulo": "Ana", "quantidades": {"chegou": 60, "orcamento": 30, "formulario": 12, "evento": 6, "pagou": 5, "avaliou": 1}, "conversao": 10.0}
  ],
  "campanhas": [{"valor": "Festa infantil SP", "rotulo": "Festa infantil SP", "quantidade": 40}, {"valor": "__sem_anuncio__", "rotulo": "Sem anúncio", "quantidade": 80}]
}
```

- `sobre_chegou` e `passagem` em porcentagem com uma casa (`null` sem base). `conversao` = evento ÷ chegou.
- `campanhas` lista as opções do filtro da coorte do período (antes do filtro de campanha).
- 422 com `fields.inicio`/`fields.fim` (data inválida, `inicio` > `fim`, mais de 366 dias), `fields.canal`,
  `fields.dividir`; 403 sem o papel.

## `GET /api/conversas/funil/parados` (gate `pode_conversas`)

Query: as mesmas de período, canal e campanha, mais `etapa` (uma das seis).

```json
{"etapa": "orcamento", "rotulo": "Orçamento enviado", "total": 18, "conversas": [
  {"id": 31, "nome": "Ana Souza", "canal": "whatsapp", "vendedor": "Bia", "primeiro_contato": "2026-11-03T14:10:00+00:00", "campanha": "Festa infantil SP"}
]}
```

- Até 200 conversas (`total` traz o número inteiro), do primeiro contato mais recente para o mais antigo.
- 422 com `fields.etapa` e os do período.

## `GET /api/clientes/<id>/linha-do-tempo` (gate `_require_vendas`: Comercial, Financeiro, Superadmin)

```json
{"marcos": [
  {"tipo": "evento", "quando": "2026-11-05T13:00:00+00:00", "titulo": "Evento fechado", "detalhe": "Festa da Sofia · 12/12/2026", "link": {"tipo": "evento", "id": 901}},
  {"tipo": "contato", "quando": "2026-11-01T18:02:00+00:00", "titulo": "Primeiro contato pelo WhatsApp", "detalhe": null, "link": {"tipo": "conversa", "id": 31}}
]}
```

- Do mais novo para o mais antigo; até 300. `link` só quando a pessoa abre a tela de destino (`conversa` e
  `orcamento`: Comercial e Superadmin). 404 ficha inexistente; 403 sem o papel.
