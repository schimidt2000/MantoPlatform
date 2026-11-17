# Contratos da API — 350 base autorizada

Erros no envelope `json_error` (`{"error": {"message", "fields"}}`). `COM` = Comercial, `FIN` =
Financeiro, `SUP` = Superadmin. Campo novo de payload existente é opcional no React.

## Ficha (alterado)

### `GET /api/clientes/<id>` — COM, FIN, SUP (gate de hoje)

Chaves novas:

```jsonc
{
  "pode_prospectar": true,
  "consentimentos": {
    "novidades": {"ativo": true, "aceite_em": "2026-11-17T10:00:00", "origem": "Conversa",
                  "versao": "2026-11-17", "retirada_em": null, "retirada_origem": null},
    "criancas": [{"id": 1, "primeiro_nome": "Lia", "nascimento": "2021-03-12",
                  "aceite_em": "…", "origem": "…", "versao": "…"}],   // só COM/SUP; chave ausente p/ FIN
    "historico": [{"tipo": "novidades", "acao": "aceite", "em": "…", "origem": "…", "versao": "…",
                   "texto": "…", "referencia": "conversa:12", "autor": "Ana"}],
    "textos": {"novidades": {"texto": "…", "versao": "…"}, "aniversario": {"texto": "…", "versao": "…"}},
    "origens": ["Conversa", "Resposta ao orçamento", "Telefone", "Pessoalmente"]
  },
  "indicado_por": {"id": 7, "name": "Carla"} ,     // ou null
  "indicacoes": [{"id": 9, "name": "Bia"}],
  "parceiro": {"id": 3, "nome": "Buffet Alegria", "tipo": "buffet"},   // ou null
  "flags": {"pode_editar_base": true}               // COM/SUP
}
```

### `GET /api/clientes/` — chave nova `flags: {"pode_editar_base": bool}`.

## Consentimentos — `clientes_base_write.py` (COM, SUP)

| Método | Rota | Corpo | Respostas |
|---|---|---|---|
| POST | `/api/clientes/<id>/consentimentos/novidades` | `{origem, referencia?}` | 200 `{consentimentos, pode_prospectar}`; 400 `fields.origem`; 403; 404 |
| DELETE | `/api/clientes/<id>/consentimentos/novidades` | `{origem, referencia?}` | 200 (idempotente); 400; 403; 404 |
| POST | `/api/clientes/<id>/criancas` | `{primeiro_nome, nascimento: "AAAA-MM-DD", aceite: true, origem}` | 201 `{consentimentos}`; 400 `fields.{primeiro_nome,nascimento,aceite,origem}`; 403; 404 |
| DELETE | `/api/clientes/<id>/criancas/<cid>` | — | 200 `{consentimentos}`; 403; 404 (criança de outra ficha também) |
| PATCH | `/api/clientes/<id>/indicacao` | `{indicado_por_id?: int\|null, parceiro_id?: int\|null}` | 200 `{indicado_por, parceiro}`; 400 `fields.indicado_por_id` (própria ficha, inexistente), `fields.parceiro_id` (inexistente, inativo); 403; 404 |

`origem` na retirada aceita a mesma lista; a referência é livre (até 80) e o cabeçalho da conversa manda
`conversa:<id>`.

## Parceiros

| Método | Rota | Papéis | Corpo / resposta |
|---|---|---|---|
| GET | `/api/parceiros?inativos=1` | COM, FIN, SUP | `{items: [{id, nome, tipo, tipo_label, contato, telefone, email, comissao_percentual: "10.00", observacao, ativo, clientes: 3}], tipos: [{valor, rotulo}], flags: {pode_editar}}` |
| POST | `/api/parceiros` | COM, SUP | `{nome, tipo, contato?, telefone?, email?, comissao_percentual, observacao?}` → 201 item; 400 `fields` |
| PATCH | `/api/parceiros/<id>` | COM, SUP | mesmos campos + `ativo` → 200 item; 400; 404 |

## Aniversários

`GET /api/clientes/aniversarios?dias=60` — COM, SUP. `dias` 1–120 (padrão 60).
`{items: [{crianca_id, primeiro_nome, data: "2026-12-01", dias: 14, idade: 5, cliente: {id, name,
phone_display}}], dias: 60}` em ordem de `data`.

## Pós-evento

| Método | Rota | Papéis | Detalhe |
|---|---|---|---|
| GET | `/api/pos-evento` | COM, SUP | `{items: [{event_id, titulo, start_at, cliente: {id, name}\|null, situacao: "pendente"\|"copiado"\|"conversa", registrado_em, avaliacao_recebida}]}` — últimos 7 dias até agora |
| GET | `/api/events/<id>/pos-evento?fotos_url=` | COM, SUP | `{mensagem, link_avaliacao, fotos_url, situacao, registrado_em, avaliacao_recebida, conversa: {pode_enviar, motivo, conversa_id}}`; 409 `cancelado`; 404 |
| POST | `/api/events/<id>/pos-evento` | COM, SUP | `{canal: "copiado"\|"conversa", fotos_url?}` → 200 `{situacao, registrado_em, mensagem}`; 400 `fields.fotos_url`; 409 `cancelado`; conversa: 503 `nao_configurado`, 409 `sem_conversa` / `janela_fechada` / `envio_travado` |

## Página pública de avaliação (alterado + novo)

### `GET /api/avaliar/<token>` — público

Chave nova (ausente quando o evento não tem contratante):

```jsonc
"consentimento": {
  "primeiro_nome": "Ana",
  "recebe_novidades": false,
  "textos": {"novidades": {"texto": "…", "versao": "…"}, "aniversario": {"texto": "…", "versao": "…"}}
}
```

A mensagem de "Indicar uma amiga" não vem da API: o React a monta (`IndicarAmiga.tsx`) com o
`primeiro_nome` e o WhatsApp da Manto de `lib/lojaTema.ts` (`WHATSAPP_LOJA`, a fonte única do
número no app público). Aparece mesmo sem o bloco `consentimento` (convergência T039).

### `POST /api/avaliar/<token>/consentimento` — público, `10 per hour`

```jsonc
{"novidades": "aceitar" | "retirar" | null,
 "versao_novidades": "2026-11-17",
 "crianca": {"primeiro_nome": "Lia", "nascimento": "2021-03-12", "aceite": true} | null,
 "versao_aniversario": "2026-11-17"}
```

200 `{recebe_novidades}`; 400 `fields.{novidades,crianca.aceite,crianca.primeiro_nome,crianca.nascimento}`;
404 token; 409 `sem_ficha` (evento sem contratante), `texto_mudou` (versão diferente da atual); 410
cancelado.

## Conversas (alterado)

- `POST /api/conversas/<id>/modelo` — modelo `MARKETING` sem aceite: 409
  `{"error": {"message": "Esta cliente não autorizou receber novidades. Registre o aceite na ficha antes de enviar um modelo de marketing.", "codigo": "sem_aceite"}}`
  (mesmo formato das outras recusas de `EnvioRecusado`).
- `GET /api/conversas/<id>` e a lista: `cliente.aceite_novidades: bool` (novo).
