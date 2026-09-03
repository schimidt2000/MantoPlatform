# Feature 273 — Orçamento → evento: o evento passa a saber o que foi vendido

**Branch**: `273-orcamento-para-evento` (sobre a `239b-hotfix-carrinho-fora-de-sp`) · **Created**: 2026-09-02
**Status**: Draft · **Migration**: nenhuma

> Item 273 do plano das ondas (`specs/266-costuras-funil/ondas-2-4-plano.md`), puxado para
> agora a pedido do dono e **com escopo maior** que o planejado: o plano deixava "recalcular
> cachês do elenco a partir do orçamento" fora; aqui a equipe vendida entra. Quando esta spec e
> o plano divergem, vale a spec (regra de leitura do próprio plano).

## O pedido, nas palavras do dono

"Se o orçamento foi feito marcando a caixinha 'evento fora de São Paulo', ele já conta o valor de
transporte, tudo mais — seria legal essa integração com o orçamento. Se o evento foi vendido com
maquiagem, tem que aparecer a pessoa que tem maquiagem naquele evento. Se foram dois
coordenadores vendidos, tem que mostrar."

## O que a medição mostrou (produção, 02/09/2026, eventos futuros)

| Origem | Com orçamento vinculado | Sem orçamento |
|---|---|---|
| Criado na plataforma | 60 | 12 |
| Importado do Google Calendar | 0 | 32 |

Nos 60 com orçamento, a criação (feature 152/239) já traz a equipe: o evento 1249 nasceu com os
dois coordenadores vendidos; o 1267 nasceu com o Maquiador (removido depois à mão) e com maquiagem
marcada nos dois personagens. O que se perdia de verdade:

1. **"Fora de SP" do orçamento nunca chegava ao evento** — 8 eventos futuros com a caixinha
   marcada no orçamento e `is_outside_sp` desconhecido (só o endereço classificava; a 239b
   melhorou o endereço, mas a caixinha é a palavra da comercial). Sem a flag, sem carrinho de
   transporte — mesmo com o orçamento tendo vendido 110 km de deslocamento (evento 1267).
2. **44 eventos futuros sem orçamento vinculado** (32 do Google + 12 da plataforma) não recebem
   nada: nem equipe, nem maquiagem, nem fora de SP, nem teto de cachê. `orcamento_history_id` só
   era gravado na criação; não havia como apontar o orçamento depois.

## Solução

Um módulo puro, `app/calendar/orcamento_evento_ops.py`, vira a fonte única de "o que o orçamento
diz e como isso entra no evento", usado pela criação, pelo vínculo posterior e pela
reclassificação dentro/fora de SP.

1. **`aplicar_fora_sp_do_orcamento`** — caixinha marcada → `is_outside_sp=True`; a quilometragem
   do orçamento vira `travel_distance_km` quando o evento não tem nenhuma (é a base da parcela
   do veículo do carrinho). Caixinha desmarcada não diz nada (não rebaixa). Roda na criação a
   partir do orçamento, no vínculo e em `reclassificar_fora_de_sp` (antes do Geocoding).
2. **`aplicar_equipe_do_orcamento`** — recalcula a lista do orçamento para a duração real do
   evento (`_compute_performer_caches`) e: casa personagens por **nome normalizado** (sem
   acento/caixa/espaços) marcando `needs_makeup`, `is_singer` e o teto (`cache_cap` +
   `cache_cap_note`) onde não havia; cria **coordenadores até a quantidade vendida**, **Técnico
   de Som** (show) e **Maquiador** (alguém maquiado) quando o evento não os tem, com teto. O que
   não casa volta no relatório (`nao_casados`) — não inventa vaga: o evento do Google já tem o
   elenco pelo título. **Nunca apaga nem rebaixa.**
3. **`aplicar_valores_do_orcamento`** — venda/transporte/nota/acréscimos tipados (BV) da duração
   escolhida (1h a 4h — a régua acima de 4h fica na criação, que recalcula tudo), só em evento
   **sem venda** (D1 do plano; cortesia/permuta conta como venda); `sale_date` pela regra da 267b;
   comissão sincronizada por injeção.
4. **`PATCH /api/events/<id>/orcamento`** — `{orcamento_history_id|null, aplicar_equipe?=true,
   aplicar_valores_duracao?: 1|2|3|4, sale_date?}` (bool/string → 400). Gate `_can_manage_sale`;
   satélite → 409 + `leader_id`; orçamento de outro vendedor → 404 (superadmin vê todos); vínculo
   **atual** de outro vendedor → 409 `orcamento_de_outro` (quem não vê o orçamento não o troca nem
   solta); orçamento preso a outro evento **não cancelado** → 409 + `event_id` (1:1 entre vivos,
   também no `POST /api/events`; cancelar libera); `null` desvincula só o FK (a equipe fica).
   Chamar de novo com o mesmo orçamento **reaplica** (idempotente). Resposta = evento completo +
   `relatorio_orcamento` (`frase` humana + contagens + `nao_casados`). `venda.tem_orcamento` diz que
   há vínculo mesmo quando o resumo não vem (painel avisa "orçamento de outro vendedor").
5. **Aba Comercial → painel "Orçamento"**: com orçamento, chips do que foi vendido ("Fora de SP ·
   110 km", "2 coordenadores", "Maquiagem em 2", "Show · técnico de som"), "Abrir orçamento",
   **"Aplicar ao evento"**, "Trocar", "Desvincular", e a frase do que aconteceu. Sem orçamento,
   busca no histórico (`OrcamentoPicker`, mesma regra de dono do histórico) e, em evento sem
   venda, a opção de aplicar também os valores de 1h/2h/3h/4h. Evento importado do Google sem
   venda ganha o aviso que explica para que serve o painel.
6. **Histórico de orçamentos**: cada linha traz "Ver evento" quando há evento vivo apontando
   (um SELECT para a página inteira, não um por linha). `DELETE` de orçamento vinculado a evento
   vivo → 409 + `event_id`, mostrado na tela com o link (antes: `IntegrityError` 500 — a FK não
   tem `ondelete`); preso só a evento **cancelado** → solta o FK com log e apaga.

## Decisões

1. **Nunca apagar, nunca rebaixar.** A equipe do evento é operação viva do casting; o orçamento
   só acrescenta o que faltava e marca o que não se sabia. O contrário (sincronização bidirecional
   ou "apagar o que o orçamento não vendeu") destruiria trabalho feito à mão.
2. **Personagem casa por nome; o resto é relatado, não inventado.** "Mickey que fala" no orçamento
   e "MICKEY" no evento são a mesma pessoa? Não dá para saber; o relatório diz e a comercial decide.
3. **A caixinha manda no endereço — sempre, não só na primeira vez.** Endereço "Buffet X" não diz
   cidade; a comercial marcou fora de SP e cobrou os km. Caixinha desmarcada não rebaixa (pode ter
   sido esquecida). A revisão pegou a primeira versão devolvendo "mudou" em vez de "o orçamento
   diz": o segundo retoque de endereço (edição React, "Estimar via Google Maps" ou sync do Google)
   rebaixava para dentro de SP e zerava os km — agora os três caminhos consultam o orçamento antes.
4. **Valores só em evento sem venda** (D1): com venda digitada o vínculo é rastro.
5. **1:1 entre eventos vivos**, cancelado libera (a 224 marca cancelado em vez de apagar).
6. **Sem migration**: nada muda no schema; a garantia de banco do 1:1 fica para a 274 (índice
   parcial), como o plano previa.

## Verificação

`verify_273.py` 15/15 contra `manto_local`, Google dublado: vínculo aplica fora de SP + km, +1
coordenador, Maquiador e Técnico criados com teto, maquiagem e teto no personagem casado,
`nao_casados`, log; reaplicar idempotente e não remove vaga acrescentada à mão; nunca rebaixa teto
nem desmarca maquiagem; valores só sem venda (`valores_ignorados` com venda); 409 entre vivos e
cancelado libera; desvincular mantém a equipe; CASTING 403; orçamento alheio 404; trocar vínculo
alheio 409; satélite 409; criação pela API herda fora de SP e km; histórico traz `event_id`;
DELETE vinculado 409. Da revisão adversarial (4 lentes + céticos): endereço editado depois do
vínculo não rebaixa nem zera km; DELETE com evento cancelado solta o FK e apaga; cortesia não
recebe valores; corpo inválido → 400; `tem_orcamento` sem resumo para quem não é dono; segundo
evento do mesmo orçamento → 409. Regressão: verify_239b 7/7, verify_267b 8/8. `npm run typecheck`
limpo; `ruff` no baseline. Em tela: evento 1323 (importado do Google) → vincular → chips, papéis
novos no Casting com teto, carrinho disponível.

## Fora de escopo

Status ganho/perdido do orçamento (275); cliente do orçamento como FK (274); "Vincular a evento
existente" a partir da página do orçamento (o caminho de hoje é pela aba Comercial do evento);
sincronização reversa (evento → orçamento); apagar vagas que o orçamento não vendeu.
