# 337 — Filtro "Sem foto" no Banco de Figurinos

**Branch**: `337-figurino-sem-foto` · **Created**: 2026-11-05 · **Status**: Pronto na branch, sem deploy
(tela conferida) · **Migration**: nenhuma

## O pedido

O dono (05/11): a Lucimara manda pelo WhatsApp os pedidos de ficha (personagem + lista de peças); ele
reescreve no padrão das fichas, põe o título certo e uma foto tirada do catálogo. Quando o personagem
ainda não está no catálogo, a ficha sobe sem foto, e isso tem de virar pendência: na tela de figurinos
precisa haver um jeito de filtrar as fichas sem foto para pôr a foto depois.

As fichas do pedido de 05/11 (Cristalina, Nicolau Winter, Soldado Jingle, Confeiteira e Confeiteiro de
Natal, Mestre Splinter, Fadas Fauna e Flora, Presentes de Natal masculino e feminino, Pirata Barba Rala)
são dado, não código: entram em produção pela própria API (`POST /api/figurino` + foto), sem passar por
esta branch.

## O que muda

- **`FigurinoListPage`**: botão **"Sem foto"** ao lado do filtro de tags, com o número de fichas sem
  foto num selo dourado. Ligado, a grade mostra só as fichas sem imagem. Some quando não há pendência e
  o filtro está desligado.
- O filtro mora no endereço (`/figurinos?sem_foto=1`, `replace`), como pede a convenção de listas da
  320: o link serve para mandar a lista de pendências a quem vai fotografar.
- "Sem foto" = `photo_url` nulo no `GET /api/figurino`. O servidor já devolve o `thumbnail_url` do
  Drive quando não há foto nativa, então a ficha antiga sincronizada do Drive não conta como pendente.
- Filtro ligado e nenhuma pendência: "Todas as fichas já têm foto." no lugar de "Nenhuma ficha
  encontrada."

## Verificação

Só tela (nenhum contrato de API muda; o filtro é sobre um campo que o payload já trazia). Typecheck dos
três apps limpo. Tela aberta em `/figurinos` contra o `manto_local`: botão com "1" (1 de 634 fichas sem
foto no banco local), clique leva a `?sem_foto=1` com `aria-pressed="true"` e um card só; recarregar
mantém o filtro; 375px sem rolagem lateral.

## Fora de escopo

Ficha com `photo_filename` gravado mas arquivo ausente no disco não conta como "sem foto" (o card mostra
o 📷 do `<Foto>`, mas o filtro olha o banco). A busca e as tags da mesma tela continuam em `useState`, fora
do endereço — não foram migrados de passagem.
