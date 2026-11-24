# Contrato — API da conferência de personagens (360)

Todas as rotas: `@api_login_required` + `_require_superadmin()` no início da view (401 sem login, 403
`"Sem permissão"` para os demais papéis). Erro no envelope de `json_error`. Núcleo:
`app/admin/catalog_conferencia_ops.py`.

## Leitura — `app/api/admin_catalogo_conferencia_read.py`

### `GET /api/admin/catalogo/conferencia?tipo=&situacao=&q=`

Fila inteira (sem paginação), ordenada por nome sem acento e depois `id`.

- `tipo`: `tema` | `dupla` | `avulso` | `generico` (filtra pelo tipo **decidido**; item sem leitura não
  tem tipo e só aparece sem este filtro ou com `situacao=sem_leitura`)
- `situacao`: `a_conferir` | `conferido` | `sem_leitura`
- `q`: nome do item, sem acento e sem caixa
- valor desconhecido em `tipo`/`situacao` é ignorado (filtro vazio)

```json
{
  "contadores": {
    "fila": 352, "a_conferir": 352, "conferidos": 0, "sem_leitura": 0,
    "por_tipo": {"tema": {"total": 117, "conferidos": 0}, "dupla": {…}, "avulso": {…}, "generico": {…}}
  },
  "leitura": {"itens_no_arquivo": 356, "a_carregar": 0},
  "itens": [
    {"id": 700, "nome": "Star Wars", "capa_url": "/catalogo/midia/….jpg",
     "situacao": "a_conferir", "tipo": "tema", "tipo_lido": "tema",
     "personagens": 11, "conferido_em": null, "conferido_por": null}
  ]
}
```

Os contadores são sempre da fila inteira, não do filtro. `leitura.a_carregar` = itens do arquivo que
existem no catálogo e ainda não têm conferência (é o que mostra o botão "Carregar leitura").
Item sem leitura: `situacao: "sem_leitura"`, `tipo: null`, `personagens: 0`.

### `GET /api/admin/catalogo/conferencia/<item_id>?tipo=&q=`

```json
{
  "item": {"id": 700, "nome": "Star Wars", "categorias": ["Filmes/Séries"],
           "fotos": [{"id": 5101, "url": "/catalogo/midia/….jpg"}]},
  "na_fila": true,
  "situacao": "a_conferir",
  "conferencia": {
    "tipo": "tema", "tipo_lido": "tema", "nota": "…", "acao": null, "grupo": null, "lote": "piloto",
    "ficha": null, "ficha_sugerida": null, "observacao": null,
    "conferido_em": null, "conferido_por": null,
    "personagens": [
      {"id": 9001, "origem": "leitura", "nome": "Yoda", "nome_lido": "Yoda",
       "foto": {"url": "/catalogo/midia/8c47….jpg", "largura": 905, "altura": 1200,
                "recorte": [29, 23, 33, 60]},
       "ficha": {"id": 415, "nome": "Yoda", "foto_url": "/uploads/…"},
       "ficha_sugerida": {"id": 415, "nome": "Yoda", "foto_url": "/uploads/…"},
       "aviso": null, "sem_foto_lido": false, "sem_foto": false,
       "decisao": "criar", "observacao": null}
    ]
  },
  "anterior_id": 699, "proximo_id": 701
}
```

- `conferencia: null` e `situacao: "sem_leitura"` quando o item não foi lido.
- `na_fila: false` quando o item existe mas saiu da fila (ganhou elenco, ficha, foi desativado ou é
  página própria); a conferência, se houver, vem junto para consulta.
- `foto: null` quando o personagem não tem foto utilizável.
- `anterior_id`/`proximo_id`: vizinhos **a conferir** na ordem da fila, respeitando `tipo` e `q`;
  `null` quando não há.
- 404 `"Item não encontrado."` se o item não existe.

## Escrita — `app/api/admin_catalogo_conferencia_write.py`

Toda rota de decisão devolve o bloco `conferencia` atualizado (mesmo formato do detalhe) dentro de
`{"conferencia": {…}, "situacao": "…"}`.

| Rota | Corpo | Recusas |
|---|---|---|
| `POST /api/admin/catalogo/conferencia/carregar` | — | — |
| `PATCH /api/admin/catalogo/conferencia/<item_id>` | qualquer de `tipo`, `ficha_id`, `observacao` | 400 campo; 404; 409 `conferido` |
| `POST /api/admin/catalogo/conferencia/<item_id>/conferir` | — | 400 (`tipo`, FR-017); 404; 409 `conferido` |
| `POST /api/admin/catalogo/conferencia/<item_id>/reabrir` | — | 404; 409 `nao_conferido` |
| `POST /api/admin/catalogo/conferencia/<item_id>/personagens` | `nome`, `ficha_id?` | 400 campo; 404; 409 `conferido` |
| `PATCH /api/admin/catalogo/conferencia/personagens/<id>` | qualquer de `nome`, `ficha_id`, `decisao`, `sem_foto`, `observacao` | 400 campo; 404; 409 `conferido` |
| `DELETE /api/admin/catalogo/conferencia/personagens/<id>` | — | 404; 409 `conferido`; 409 `da_leitura` |

- 404 em rota de item: item inexistente **ou** item sem leitura (`"Este item ainda não tem leitura."`).
- 409: `{"error": {"message": "…", "fields": {}, "codigo": "conferido"}}`.
- Campo ausente no corpo do `PATCH` = não mexe. `ficha_id: null` = tira a ficha.

### Resposta da carga

```json
{"itens_novos": 356, "personagens_novos": 715, "ja_existiam": 0,
 "ignorados": [{"id": 999, "nome": "…", "motivo": "O item não existe mais no catálogo."}]}
```

## Textos (app interno, Princípio XV)

| Onde | Texto |
|---|---|
| Entrada na lista do catálogo | "Conferir personagens" |
| Título da fila | "Conferência de personagens" |
| Progresso | "120 de 352 conferidos" |
| Ação principal da fila | "Continuar conferência" |
| Situações | "A conferir" · "Conferido" · "Sem leitura" |
| Filtro de situação | "Todas as situações" |
| Fila vazia no filtro | "Nenhum item encontrado." |
| Fila zerada | "Todos os itens da fila foram conferidos." |
| Sem leitura carregada | "A leitura das fotos ainda não foi carregada." + botão "Carregar leitura" |
| Carga feita | "Leitura carregada: 356 itens e 715 personagens." / "Nenhum item novo na leitura." |
| Item sem leitura | "Este item ainda não tem leitura das fotos. Cadastre o elenco no catálogo." + "Ver no catálogo" |
| Item fora da fila | "Este item saiu da fila: já tem elenco ou ficha no catálogo." |
| Decisão do personagem | "Criar" · "Não criar" · "Criar sem foto" |
| Referência da leitura | "A leitura propôs: Piloto Rebelde" · "Ficha sugerida: 417 Luke Skywalker" |
| Acrescentar | "Acrescentar personagem" · "Informe o nome do personagem." |
| Excluir acrescentado | "Excluir este personagem?" · "Excluir" |
| Rodapé | "Conferir" · "Conferir e ir para o próximo" · "Reabrir" |
| Conferido | "Conferido por Gabriella em 24/11 às 15h10." |
| 409 conferido | "Este item já foi conferido. Reabra o item para alterar." |
| 409 da leitura | "Personagem da leitura não pode ser excluído. Marque como \"Não criar\"." |
| Erro genérico | "Não foi possível salvar. Tente novamente." |
