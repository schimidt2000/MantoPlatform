# 336b — O vínculo da tag NFC só lista eventos de hoje em diante

**Branch**: `336b-tag-nfc-so-eventos-futuros` · **Created**: 2026-11-10 · **Status**: Em produção desde
10/11/2026 ~22h (`verify_336b.py` 8/8, `verify_336.py` 7/7) ·
**Migration**: nenhuma

## O pedido

Roberto (repassado pelo dono em 10/11): as datas na lista ajudaram muito a vincular os eventos às
tags; eventos que já aconteceram poderiam não aparecer na lista de possibilidades. O dono confirmou:
a tag é vinculada antes da festa em 99% dos casos. Depois de ver a primeira versão: "ensaios e outros
compromissos não devem aparecer".

## O que muda

- **`search_events(q, limit, upcoming=False)`** (`app/calendar/event_ops.py`): com `upcoming`, a busca
  de texto só traz eventos com `start_at` de hoje 0h em diante (relógio de São Paulo), do mais próximo
  ao mais distante. A busca por data ignora o filtro: quem digita "22/08" pediu aquele dia.
- **`only_bookings` / `so_festas=1`**: tira o compromisso interno (título começando com 🟧 ou 🟠 —
  ensaio, visita técnica, gravação, empréstimo de figurino; `MARCADORES_COMPROMISSO_INTERNO`) da busca
  de texto e da busca por data. O diálogo da tag passa sempre, com ou sem passados.
- **`GET /api/agenda/search?futuros=1`** liga o filtro. Sem o parâmetro nada muda (agenda, vínculo de
  ensaio e Pix recebido seguem vendo o passado).
- **`useAgendaSearch(q, { futuros })`** e **`AssociarDialog`**: o diálogo da tag busca com `futuros`;
  abaixo do campo, "Mostrando eventos de hoje em diante." e o botão "Mostrar os que já aconteceram"
  (que volta com "Só de hoje em diante"). Fechar o diálogo volta ao padrão.

## Verificação

`verify_336b.py` (8 cenários; os dois de `so_festas`: sem o parâmetro "ensaio" ainda traz ensaios, e
com ele nenhum título 🟧/🟠 em texto nem na data de um dia com ensaio e festa): sem login 401; sem `futuros` a ordem segue decrescente; com `futuros=1`
nada antes de hoje e ordem crescente; ids batem com o SELECT direto (conexão separada); data passada
digitada com `futuros=1` ainda devolve o evento; limpeza. Rodado no espelho `manto_336b` (dump de
10/11 + `flask db upgrade`), porque o `manto_local` está atrás das migrations 338 a 342. Tela aberta em
`/3d/tags`: "show" lista de 10/11 em diante; com o botão ligado, volta a lista com passados. O
`so_festas` entrou depois dessa conferência e foi provado pela API (a tela só ganhou o parâmetro).

## Fora de escopo

As outras telas que usam a busca não mudam.
