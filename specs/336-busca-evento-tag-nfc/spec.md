# 336 — Buscar o evento por data no vínculo da tag NFC

**Branch**: `336-busca-evento-tag-nfc` · **Created**: 2026-11-05 · **Status**: Entregue na branch
(`verify_336.py` 7/7, tela conferida), aguardando o merge a pedido do dono · **Migration**: nenhuma

## O pedido

O dono (05/11): na página de tags NFC, vincular um evento é difícil. A busca mostra o nome da
cliente mas não a data; o ideal é poder buscar por data, pelo nome da cliente ou pelo título do
evento. A "mini foto" da opção aparece bugada ("0 ()", coisa estranha); seria melhor ver o nome do
evento e a data.

## O que muda

- **Causa.** O rótulo era `título — data`, mas o título tem cinco personagens e o `truncate` cortava
  a data do fim. A miniatura era o placeholder de iniciais do `AvatarThumb`: primeira letra da
  primeira palavra + da última, que num título "(R&I) BLUEY + BINGO" vira "(B", e com emoji vira
  meio caractere.
- **`search_events` (`app/calendar/event_ops.py`)**: termo que é data (`07/11`, `7/11/26`,
  `07-11-2026`, `2026-11-07`) busca SÓ pelo dia do evento; sem ano, o dia/mês em qualquer ano, o mais
  recente primeiro. Data impossível (`31/02`) cai na busca de texto. Sem o desvio, "07/11" virava os
  dígitos "0711" e casava telefone por acaso. Vale para todo consumidor de `GET /api/agenda/search`
  (busca da agenda, vínculo de ensaio, Pix recebido, tag NFC); o contrato não muda.
- **`AssociarDialog` (tag NFC)**: a opção de evento mostra o título inteiro na primeira linha e
  "sáb, 07/11/2026 · 20h30 · Cliente" na segunda; a miniatura vira um calendarinho com o dia e o mês.
  Placeholder "Data (07/11), personagem, cliente ou telefone…", dica antes de digitar e mensagem de
  vazio que sugere a data. O "atual:" mostra a data do evento vinculado.

## Verificação

`specs/336-busca-evento-tag-nfc/verify_336.py` contra o `manto_local`: sem login 401; "07/11" só traz
7 de novembro, sem cancelado; quatro formatos com ano devolvem o mesmo conjunto; ids batem com o
SELECT direto (conexão separada); "31/02" não quebra; "ariel" segue achando pelo título. Tela aberta
em `/3d/tags` com "07/11" digitado (sem selecionar, porque selecionar salva).

## Fora de escopo

As outras telas que usam a mesma busca (ensaio, Pix) ganham a busca por data mas não mudam o
desenho das opções. Busca combinada ("ariel 07/11") não existe: o termo é data ou texto.
