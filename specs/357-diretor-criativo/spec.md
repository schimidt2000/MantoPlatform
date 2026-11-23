# 357 — Diretor criativo: o pedido de peça sai concreto

**Branch**: `357-diretor-criativo` · **Created**: 2026-11-19 · **Status**: Pronto na branch, sem push ·
**Migration**: nenhuma · Nível 2 (harness: agente, skill e script de leitura; nenhum código do app muda)

## O pedido

O dono, em 19/11, sobre os dois pedidos de peça abertos pela 1ª rodada de marketing (cards 68 e 69, 17/11):
"ficou muito genérico. Quero que tenha um agente especializado em criar essas narrativas para que os
pedidos sejam mais concretos".

O texto de 17/11 dizia "crianças rindo com personagem autoral — fada, palhaço, robô de LED ou show de
luz". Não dizia qual tema, qual foto, qual festa, qual momento, quantos segundos nem qual texto. Havia
uma razão: nenhum tema estava (nem está) liberado para anúncio.

## O que muda

1. **`.claude/agents/diretor-criativo.md`** (novo). É o agente que escreve o pedido de peça. Ele traz:
   - o teste do pedido pronto e quem compra em cada frente;
   - as regras: só tema liberado, sem IA, autorização de imagem de criança, música só da Meta, nada que
     a vendedora não cumpra;
   - a ordem do material: festa da agenda, depois a foto do catálogo, depois o Drive;
   - a estrutura por formato (foto 4:5/9:16; vídeo com roteiro por segundo e lista de takes);
   - os textos exatos (letreiro, texto principal, título, mensagem pronta do WhatsApp), a medida com
     a variação A/B e o JSON no formato do `POST /pedidos`.

   Ele só lê. Quem grava é a rotina (CLAUDE.md §8: subagente não edita).
2. **`scripts/marketing/criativo_dados.py`** (novo). Lê a produção só em leitura (`.railway-db-url`,
   `default_transaction_read_only`) e traz:
   - os temas não licenciados, com a situação, a página e as fotos do catálogo;
   - os personagens mais pedidos em 120 dias;
   - as próximas festas: data, hora, cidade, personagens e se há Foto/Vídeo escalado. Não leva nome de
     cliente, rua, número nem CEP.
3. **Skill `marketing-auditor`, passo 11**: a rotina decide o quê (frente, formato, conceito pelos
   números) e o agente escreve o pedido. Antes de gravar, a rotina confere o tema, a privacidade e se o
   pedido não é repetido. O `platform` do card é a rede social. O que "Depende de: liberar <tema>" vai
   para o relatório.
4. **`scripts/marketing/README.md`**: seção "Pedidos de peça" e a URL de leitura em "Segredos".
5. **Cards 68 e 69 reescritos em produção** com o texto do agente, na sessão do dono.
6. **`scripts/marketing/drive_indice.py`** (novo, pedido do dono em 19/11: "já tenho um Google Drive bem organizado
   com uma porrada de arquivos"). Lê o Drive montado no disco (`G:\My Drive`, Google Drive para computador), **só nas
   pastas de marketing** (lista fechada), e grava um índice fora do repositório (`~/.manto-drive/indice.sqlite`): caminho,
   tema, sessão, tipo (foto editada/bruta, arte, vídeo pronto/bruto/ensaio) e tamanho, sem baixar nada. `temas` e `buscar`
   respondem o que existe; `ver` baixa só o arquivo pedido e gera a prévia (foto 1024 px; vídeo em quadros com o segundo)
   e diz se aguenta 4:5 e 9:16. O agente passa a preferir o Drive (material pronto, em resolução cheia), depois a festa da
   agenda e por último o catálogo; a rotina refaz o índice no passo 0.

## Verificação

- O `criativo_dados.py` rodou contra a produção em 19/11. Trouxe 446 temas não licenciados (0
  liberados), os personagens mais pedidos e as festas de 21 dias. O campo "cidade" sai sem rua, número
  nem CEP (conferido na lista inteira). `ruff check` e `ruff format` limpos.
- O agente rodou com os dados de 19/11 e devolveu os pedidos que substituem os cards 68 e 69, no
  formato do `POST /pedidos`, mais a lista de temas para liberar.
- Os cards 68 e 69 foram reescritos pela tela, na sessão do dono, e conferidos pela API:
  - 68: Fada Glow Peach, foto 6 do catálogo, entrega 25/11;
  - 69: Papai Noel com Bailarelfos, captação no evento de 20/11 em Sorocaba, entrega 24/11.
- A tela ensinou uma regra que o agente agora segue: "Objetivo" e "Texto do letreiro" são campos de
  uma linha só. O texto longo vai em "O que mostrar" e "Observações".
- Índice do Drive em 23/11: 45.753 fotos e vídeos em 66 s (Temas Manto Produções 43.132; o resto das pastas de marketing
  2.621); as pastas de projeto e cache do Premiere ficam fora. Busca de Fadas Glow: 36 fotos editadas (3072×4608) e 1
  vídeo pronto (`EXPORT/FADAS_GLOW_V03.mp4`, 1080×1920, 60 s); prévias abertas e conferidas. `ver` recusa caminho fora das
  pastas de marketing (testado com Financeiro). `ruff check` limpo.
- Não há verify Python: nenhum comportamento do app muda.

## Fora de escopo

- Endpoint para a rotina editar um pedido já aberto. Hoje a edição é pela tela, por uma pessoa.
- Ler o Drive "Temas Manto Produções" direto. O agente aponta a pasta e quem abre é a equipe.
- Liberar temas para anúncio: é decisão do Superadmin em Marketing › Temas.
