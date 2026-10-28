# 309b — A Visita Mágica no orçamento diz o que se entrega: até 30 minutos

**Branch**: `309b-visita-magica-30-minutos` · **Created**: 2026-10-28 · **Status**: PRONTA, aguardando deploy ·
**Migration**: nenhuma (a tabela de preços é JSON em `site_settings.pricing_config`)

## O pedido

O dono (28/10), com a arte da campanha "Visita Mágica" anexada: o orçamento dos pacotes de Natal diz que a
visita é de uma hora, mas ela é de **até 30 minutos**; o orçamento tem de passar algo "totalmente condizente
com o produto oferecido de verdade". Decidiu (pergunta com prévia da mensagem): **duração + o que inclui**,
editável na tabela de preços, na mensagem e no PDF.

A arte: chegada mágica; duração de até 30 minutos; músicas natalinas junto à família; entrega de presentes
(até 10, fornecidos pelo contratante); ao final, mensagem especial sobre o verdadeiro significado do Natal.
Preços (2.500 / 3.600 até 23/12; 5.000 / 6.500 em 24 e 25/12) já batiam com a tabela — não mudam.

## O que muda

- `app/orcamento/settings.py`: produtos padrão com descrição "visita de até 30 minutos" e campo novo
  `detalhes` ("o que inclui", uma linha, até 300) com o texto da arte. `_migrar_309b`, dentro do `load()`:
  descrição EXATAMENTE "visita padrão, até 1h" vira a nova; Visita salva sem a chave `detalhes` ganha o
  texto da arte. Edição do time e produto criado pelo time não são tocados. `validar_produtos` aceita e
  limita `detalhes` (quebra de linha vira espaço).
- `app/orcamento/produtos.py`: `detalhes` no produto resolvido e em `quote.produtos`; a mensagem põe
  `_detalhes_` em itálico logo abaixo da linha do produto (uma vez por texto — dois exemplares não repetem).
- `app/orcamento/pdf.py`: o mesmo texto em itálico sob a linha do produto, até 3 linhas.
- Tela "Configuração de preços" → "Produtos de tabela": caixa "O que inclui".
- Orçamento já salvo não muda (o `quote` congelado não tem `detalhes`; o PDF dele sai como era).

## Verificação

`verify_309b.py` (10/10, `verify_309b_final.txt`), só leitura: tabela do `manto_local` com os produtos
como a 309 os gravava, migrada em memória; `settings.load` dublado nos cálculos. No código de antes, 0/10
(`verify_309b_primeira_falha.txt` — o cenário 4 cai em "mensagem ainda fala em 1 hora"). `ruff check`,
`npm run typecheck` e tela aberta (configuração de preços e calculadora, backend na 5011 com o código novo).

## Fora de escopo

Mostrar o "o que inclui" no card da calculadora (a vendedora lê na mensagem); mudar preço ou composição;
texto de "valores para a Grande São Paulo" (a mensagem já trata deslocamento fora de SP).
