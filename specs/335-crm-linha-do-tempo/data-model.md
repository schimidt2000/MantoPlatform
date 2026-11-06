# Modelo de dados — 335 Linha do tempo da ficha e funil das conversas

**Nenhuma tabela, coluna ou migration nova.** Tudo é leitura do que existe; as estruturas abaixo são as de saída.

## Fontes

| Fonte | Liga à conversa / à ficha por | Fuso |
|---|---|---|
| `conversas` | `client_id` (SET NULL), `responsavel_id`, `canal` | UTC |
| `conversa_mensagens` (`direcao = 'recebida'`) | `conversa_id` | UTC (`momento`) |
| `conversa_anuncios` + `anuncios_meta` | `conversa_id`; campanha pelo `anuncio_id` | UTC |
| `orcamento_envios` | `conversa_id`, `orcamento_id` | UTC |
| `orcamento_history` | `client_id` (333) | UTC |
| `form_responses` | `client_id` | UTC |
| `event_clients` + `calendar_events` | `client_id`; vivo = `cancelled_at IS NULL`; grupo = `group_leader_id` | `created_at` UTC; `start_at` São Paulo |
| `event_payments` (+ `pix_recebidos.recebido_em`) | `event_id` | UTC (`created_at`); São Paulo (`recebido_em`) |
| `client_feedbacks` | `event_id` | UTC (`submitted_at`) |
| `clients` | — | `created_at` UTC; `kommo_created_at` São Paulo |

## Saída: etapa do funil

```text
ETAPAS = chegou → orcamento → formulario → evento → pagou → avaliou
etapa mais avançada(conversa) = a última etapa cujo fato aconteceu depois do primeiro contato (chegou, se nenhum)
conta(etapa) = #conversas com etapa mais avançada >= etapa
parou_em(etapa) = conversas com etapa mais avançada == etapa
```

## Saída: marco da ficha

```text
{tipo, quando (ISO com fuso), titulo, detalhe?, link? {tipo: conversa|orcamento|evento, id}}
tipo ∈ entrada | contato | anuncio | orcamento | formulario | evento | pagamento | avaliacao
```
