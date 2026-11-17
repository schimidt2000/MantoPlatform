# Contratos — 328 Conversas em equipe

Todos com `api_login_required` e o gate `pode_conversas()` (COMERCIAL/SUPERADMIN, papel real) no início da
view. Erro no envelope de `json_error`, com `codigo` quando a tela precisa agir.

## Mudanças no que já existe (325)

- `GET /api/conversas` ganha `filtro=todas|minhas|sem_responsavel` (padrão `todas`; outro valor → 422
  `fields.filtro`). Cada conversa ganha:
  - `responsavel`: `{id, nome}` ou `null`;
  - `aguardando_desde`: ISO `+00:00` ou `null`.
- `GET /api/conversas/<id>` ganha, em `conversa`, `responsavel`, `aguardando_desde` e `responsavel_ativo`
  (falso quando o responsável perdeu o papel). Ganha também, no topo, `notas`:
  `[{id, texto, autor: {id, nome} | null, momento}]`, em ordem.
- `POST /api/conversas/<id>/mensagens` aceita também `audio/webm` (convertido para ogg). A conversão que falha
  devolve 422 `fields.arquivo`.

## `GET /api/conversas/equipe`

As pessoas para quem se pode transferir: `{"equipe": [{"id", "nome"}]}`. São os usuários ativos, com acesso e
papel COMERCIAL ou SUPERADMIN, por nome.

## `POST /api/conversas/<id>/responsavel`

Corpo: `{"acao": "assumir" | "transferir" | "devolver", "responsavel_id"?: int}`.

| Ação | Sucesso | Recusa |
|---|---|---|
| `assumir` | 200 `{conversa}` com o usuário atual | 409 `codigo: "ja_assumida"`: "Esta conversa já foi assumida por {nome}." |
| `transferir` | 200 `{conversa}` com `responsavel_id` | 422 `fields.responsavel_id`: "Selecione uma pessoa da equipe." |
| `devolver` | 200 `{conversa}` com `responsavel: null` | — |

409 `codigo: "alterada"`: "Outra pessoa alterou o responsável agora. Confira e tente novamente." (corrida na
transferência ou na devolução). 404 para conversa inexistente.

## `POST /api/conversas/<id>/notas`

Corpo `{"texto": "…"}` → 201 `{"nota": {…}}`. Texto vazio ou com mais de 2.000 caracteres → 422 `fields.texto`.

## Respostas rápidas

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/conversas/respostas-rapidas` | `{"respostas": [{id, titulo, atalho, texto}]}`, por título |
| `POST` | `/api/conversas/respostas-rapidas` | `{titulo, atalho?, texto}` → 201; 422 `fields.titulo`/`fields.atalho`/`fields.texto` (vazio, longo, repetido, atalho com espaço) |
| `PATCH` | `/api/conversas/respostas-rapidas/<id>` | mesmos campos, todos opcionais → 200; 422 por campo; 404 |
| `DELETE` | `/api/conversas/respostas-rapidas/<id>` | 204; 404 |

Textos de recusa (XV): "Informe o título.", "Já existe uma resposta com este título.", "O atalho não pode ter
espaço.", "Já existe uma resposta com este atalho.", "Informe o texto.", "O texto passa de 4096 caracteres.".

## Notificações

- Kind `conversa.esperando`: título "{Nome} espera resposta há {N} min." (a partir de uma hora, "há {N} h"), corpo =
  prévia da última mensagem,
  `link_path = /conversas?c={id}`, severidade `urgent`.
- Kind `conversa.transferida`: título "{Quem} transferiu a conversa com {Nome} para você.", `link_path =
  /conversas?c={id}`, severidade `info`, só para o destino. `dedupe_key =
  "conversa.transferida:{id}:{epoch de assumida_em}"`.
