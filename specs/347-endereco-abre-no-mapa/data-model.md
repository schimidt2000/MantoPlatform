# Modelo de dados — Feature 347

Nenhuma mudança de banco, modelo, migration ou payload.

O dado lido é o endereço que as telas já recebem:

| Tela | Campo (já no payload) | Origem |
|---|---|---|
| App interno — página do evento (cabeçalho e "Dados do evento") | `event.location: string \| null` | `serialize_event_detail` (`app/api/agenda_read.py`), tipo em `apps/internal/src/lib/agenda.ts` |
| Portal — "Próximos eventos" e "Convites" | `PortalRole.location: string \| null` | `portal_ops.get_agenda`, tipo em `apps/portal/src/lib/portalAgenda.ts` |

Regra da interface: `location` vazio, só com espaços ou `null` → nada tocável (FR-008).

## Valor derivado (só no navegador)

`OpcaoDeMapa` — montado por `linksDeMapa(endereco)` em `@manto/ui`:

| Campo | Tipo | Valor |
|---|---|---|
| `app` | `"google" \| "apple" \| "waze"` | identificador estável |
| `rotulo` | `string` | "Google Maps", "Apple Mapas", "Waze" |
| `url` | `string` | link universal da pesquisa R1, com o endereço codificado |

Sempre três, nesta ordem, ou nenhum.
