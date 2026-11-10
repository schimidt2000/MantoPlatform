# Modelo de dados — 341

## `virtual_campaigns.recorded_delivery_until` (nova)

| Tipo | Nulo | Default | Para quê |
|---|---|---|---|
| `date` | sim | — | data em que todo vídeo vendido até ela fica pronto ("Entrega dos vídeos até") |

Regra (`virtuais_ops.prazo_do_video(campanha, hoje)`):

- `recorded_delivery_until` preenchida e `hoje <= recorded_delivery_until` → a data;
- senão → `hoje + recorded_delivery_days` (o comportamento de antes).

O resultado vai para `VirtualMediaDelivery.due_date` na efetivação do vídeo; a página do pedido
(`recorded_due_date`), a Fila de Produção e o e-mail de compra leem dali.

Migration `e341a1b2c3d4` (`down_revision = e340c1a2b3d4`), aditiva: `add_column` nulo; `downgrade`
derruba a coluna.

## API

- `GET /api/virtuais/campanhas/<slug>` (público) e `GET /api/virtuais/campanhas/<id>/admin`:
  `recorded_delivery_until: "2026-12-13" | null`.
- `POST /api/virtuais/campanhas` e `PATCH /api/virtuais/campanhas/<id>`: aceitam
  `recorded_delivery_until` (`AAAA-MM-DD`, vazio ou `null` limpa); inválida → 400 com
  `fields.recorded_delivery_until`.
