# Hotfix 239b — o carrinho de transporte some porque "fora de SP" fica desconhecido

**Branch**: `239b-hotfix-carrinho-fora-de-sp` · **Created**: 2026-09-02 · **Status**: Draft · **Migration**: nenhuma

## Sintoma

"O botão do carrinho (🚗 Marcar transporte / Leva o carro) não está aparecendo em todos os
eventos." O botão existe desde a 239 (decisão 4: *carrinho só disponível quando
`event.is_outside_sp`*), e o casting precisa dele para o teto de cachê de quem leva o carro subir
a parcela do veículo.

Medido em produção em 02/09/2026, eventos futuros (a partir de 7 dias atrás):

| `is_outside_sp` | eventos |
|---|---|
| `false` (dentro de SP) | 47 |
| **`NULL` (desconhecido)** | **55** |
| `true` (fora de SP) | 2 |

Entre os 55 "desconhecidos": Porto Feliz, Santo André, Jundiaí, São José dos Campos, Suzano,
Carapicuíba, Mogi das Cruzes, Alphaville, São Bernardo do Campo, Belém do Pará. Nenhum tem CEP no
endereço; nenhum tem a palavra "São Paulo". No histórico inteiro, só 3 eventos foram `true`.

## Causa

`_lookup_sp_status(location)` (`app/calendar/routes.py`) só sabia dois truques: CEP no texto →
ViaCEP; ou a palavra "São Paulo" no texto → dentro. Endereço real de festa é "Buffet X -
Alphaville" ou "Fazenda Y, Porto Feliz": sem CEP, sem "São Paulo" → `None`. E `None` é tratado
como "não é fora": o botão não renderiza (`foraDeSP = Boolean(...)`) e o `POST /roles/<id>/transporte`
recusa com 400. Agrava: as duas edições React (`update_event_core`, `update_event_dados`) trocam o
endereço sem reclassificar — só a criação e o sync do Google classificavam.

## Solução

1. **Geocoding do Google entre o CEP e o fallback por texto** — `maps.cidade_do_endereco()`
   devolve município e UF (`administrative_area_level_2` → `locality`; UF de
   `administrative_area_level_1`). Testado com a chave de produção em 10 endereços reais: Porto
   Feliz, Barueri (Alphaville), Jundiaí, Carapicuíba e Belém/PA saíram como fora; Tatuapé,
   Pinheiros, Campo Belo e "Rua Coronel Carlos Oliva, 104" como São Paulo; "buffet Kid Recanto
   Zona norte" sem resultado → continua desconhecido (e aí entra a decisão 3).
2. **Reclassificar na edição** — `event_ops.reclassificar_fora_de_sp(event, local_mudou)`:
   endereço que mudou reclassifica; endereço igual só reclassifica se estava desconhecido (cura
   sem custo); fora de SP sem distância busca a estimativa de trajeto (é a base da parcela do
   veículo). Chamada nas duas edições React e em "Estimar via Google Maps" (`/travel-estimate`),
   que vira o botão de "tentar de novo".
3. **Desconhecido conta como fora, e marcar classifica.** O botão aparece quando
   `is_outside_sp !== false`; ao marcar transporte num evento desconhecido, o servidor grava
   `is_outside_sp = True` (quem escala é quem sabe que há carro) e tenta a estimativa. Dentro de SP
   conhecido continua sem botão e com 400 — decisão 4 preservada.
4. **Tela** — a Logística mostra "Dentro ou fora de SP: não identificado" quando `null`, ao lado
   do botão "Estimar via Google Maps".
5. **Legado** — `reclassificar_fora_de_sp.py` (dry-run por padrão; `--execute`; `--todos` inclui
   passados): os 55 futuros desconhecidos ganham classificação pelo Geocoding e, quando fora,
   distância. Custo: uma chamada por evento.

## Decisões

1. **Geocoding no servidor, com a chave que já existe**, não uma lista de cidades vizinhas: a
   lista envelhece e não cobre "Belém do Pará"; o Google já é a fonte da distância.
2. **Desconhecido ≠ dentro.** Tratar `None` como "não é fora" foi o que escondeu o botão em 55
   eventos. Quando o sistema não sabe, a pessoa decide — e a decisão fica gravada.
3. **Editar reclassifica só quando muda o endereço ou quando não se sabia.** Evento com
   classificação conhecida e endereço igual não gasta Geocoding a cada salvamento (o verify
   prova que o Google não é chamado nesse caso).
4. **Não wipe de `travel_distance_km` ao virar dentro de SP** (o Jinja zerava): a Logística mostra
   a estimativa de trajeto para qualquer evento, dentro ou fora.

## Verificação

`verify_239b.py` 7/7 contra `manto_local` com Google dublado (Geocoding por dicionário, trajeto
fixo em 42 km, Agenda no-op): lookup fora/dentro/desconhecido/texto; criação classifica e estima;
PATCH reclassifica ao trocar endereço, cura flag desconhecida e não chama o Google com flag
conhecida e endereço igual; marcar em desconhecido → 200 e vira fora com distância, dentro → 400,
fora → 200; "Estimar" reclassifica; script dry-run não grava e `--execute` classifica.
Geocoding real conferido em produção (10 endereços, acima). `npm run typecheck` limpo; `ruff` no
baseline.

## Fora de escopo

Botão dentro de SP (decisão 4 da 239 continua); reclassificar os 229 eventos passados (só com
`--todos`, para relatório); trocar ViaCEP pelo Geocoding também quando há CEP (funciona; não
mexer).
