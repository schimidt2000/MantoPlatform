# 355 — A luminária anuncia o Papai Noel até 06/12

**Branch**: `355-luminaria-anuncia-papai-noel` (da `main`) · **Created**: 2026-11-19 · **Status**: Em produção (23/11 ~19h06) ·
**Migration**: nenhuma (`virtual_campaign_visits.origem` e `virtual_orders.origem` são texto; entra o valor `luminaria`)

> Nível 2, ajuste da página pública da tag NFC (255/297) que aponta para a loja (205/344). Sem
> migration, sem endpoint novo: a página lê a vitrine pública que já existe.

## O pedido

O dono, em 19/11/2026, com a campanha "Alô Papai Noel" no ar: "coloque uma propaganda do alo.manto
em todas as luminárias até o dia 6/12".

As luminárias são as peças com tag NFC entregues às clientes. Encostar o celular na peça abre
`/nfc/<código>`, a página com o menu (mensagem especial, Spotify, Instagram). Quem tem a luminária em
casa é cliente que já comprou da Manto, quase sempre com criança. É o público da chamada com o Papai
Noel, e hoje a página não fala da loja.

## O que muda

- **Cartão do Papai Noel no menu de toda tag**, abaixo dos botões de sempre: a capa da campanha, o
  título, uma frase sobre o formato que ainda tem vaga, o "a partir de" e o botão "Ver como
  funciona", que abre `/catalogo/v/papai-noel?origem=luminaria` na mesma aba. Aparece até
  **06/12/2026** inclusive (data de São Paulo, não a do aparelho). Do dia 07 em diante a página nem
  consulta a loja.
- **Nada de oferta sem vaga.** O cartão lê a vitrine pública (`GET /api/virtuais/vitrine`): só
  aparece com a campanha `papai-noel` publicada e com horário ao vivo livre ou vídeo gravado em
  estoque. O texto acompanha o que há: chamada ao vivo no dia 6, vídeo gravado, ou os dois. O preço
  "a partir de" é o menor dos formatos com vaga. Vitrine fora do ar = menu de sempre, sem erro.
- **A loja conta as visitas que vêm da luminária.** `luminaria` entra na lista fechada de origens
  (`VIRTUAL_ORIGENS`, rótulo "Luminária"). Sem isso o `?origem=luminaria` virava "Outro" no card
  "Visitas e vendas" da campanha. A origem segue com a reserva, como as outras.
- O cartão não muda nada do que a página já faz: o menu continua igual para código inexistente
  (SC-006 da 255) e a mensagem especial continua o primeiro botão.

## Verificação

`verify_355.py` contra um espelho do dump de 19/11 02h:
1. `normalizar_origem` reduz `luminaria`/`Luminaria` a `luminaria`;
2. visita com `origem=luminaria` conta em `luminaria`, não em `outro` (conferido por conexão separada);
3. o funil da campanha mostra a linha "Luminária" e o link `?origem=luminaria`;
4. origem desconhecida continua indo para `outro`: a lista segue fechada (deve falhar se `luminaria`
   abrir a porta para qualquer texto);
5. o funil sem papel de loja segue em `403` (deve falhar);
6. limpeza, nenhuma conexão externa.

Tela, em 375 px: `/nfc/<código>` com a campanha com vaga (cartão), sem vaga (sem cartão) e com
movimento reduzido; o clique leva à campanha com `?origem=luminaria`.

## Fora de escopo

Anúncio na capa ou na abertura em vídeo (o toque da capa é o que libera o som: não pode concorrer);
cadastro de anúncios pelo app interno (é um anúncio só, com data para acabar); outras campanhas da
loja. O cartão sai do código depois de 06/12 (dívida no `docs/05`).
