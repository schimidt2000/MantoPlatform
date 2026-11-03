# Modelo de dados — 332 Avisos no celular

A migration é à mão e **aditiva**, com `down_revision = "a330c4e8f1b2"`. Relógio em UTC naive.

## `push_assinaturas` (`PushAssinatura`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | FK `users.id` CASCADE, index | dono do aparelho (a pessoa logada no último registro) |
| `endpoint` | Text, UNIQUE (`uq_push_assinaturas_endpoint`) | endereço do serviço de avisos (identifica o aparelho) |
| `p256dh` | String(255) | chave pública do aparelho |
| `auth` | String(64) | segredo de autenticação do aparelho |
| `navegador` | String(255), null | `User-Agent` cortado, para a pessoa reconhecer o aparelho |
| `created_at` | DateTime | UTC |
| `ultimo_aviso_em` | DateTime, null | UTC; o último aviso aceito pelo serviço |

O registro do mesmo `endpoint` atualiza a linha (`ON CONFLICT DO UPDATE`): o aparelho passa para a pessoa logada.
