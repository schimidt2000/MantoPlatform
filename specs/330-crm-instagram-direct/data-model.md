# Modelo de dados — 330 Instagram Direct

A migration é à mão e **aditiva**, com `down_revision = "f328b2d4e6a1"` (head da 328). Relógio em UTC naive, como as
tabelas da 325.

## `conversas`

Colunas novas:

| Coluna | Tipo | Regra |
|---|---|---|
| `usuario` | String(64), null | @usuário do Instagram, sem a arroba; vazio no WhatsApp |
| `perfil_em` | DateTime, null | UTC; última busca do perfil (sucesso ou falha). Sem nome e com mais de 24 h → busca de novo |

O que já existe e muda de uso no Instagram:

- `canal` = `"instagram"`;
- `contato_id` = IGSID;
- `nome_perfil` = nome do perfil;
- `telefone` e `client_id` ficam **sempre vazios**, porque o vínculo com a ficha é só do WhatsApp nesta fase.

## `conversa_mensagens`

| Coluna | Mudança | Por quê |
|---|---|---|
| `externo_id` | String(128) → String(255) | o `mid` do Instagram passa de 128 caracteres |
| `resposta_a` | String(128) → String(255) | idem (`reply_to.mid`) |

O que muda de uso no Instagram:

- **`externo_id`**:
  - `mid`;
  - `"{mid}#{n}"` para o n-ésimo anexo (n ≥ 1);
  - `"reacao:{mid}:{timestamp}:{acao}"` para a reação.
- **`origem`**: `outro` no eco do Instagram (app do Instagram ou Kommo).

## `conversa_midias`

Sem mudança. No Instagram, `externo_id` é nulo e o link do anexo mora no `dados` da mensagem.

## `whatsapp_avisos`

Sem mudança. Guarda também o aviso cru do Instagram (`"object": "instagram"` no corpo), e o processamento despacha
pelo `object`.
