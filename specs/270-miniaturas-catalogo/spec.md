# Feature 270 — miniaturas do catálogo: parar de baixar 1,3 MB para desenhar 64px

**Branch**: `270-miniaturas-catalogo` · **Created**: 2026-09-01 · **Status**: Draft
**Migration**: nenhuma

## Problema

A 268 atacou o **peso** das fotos (compressão) e a **repetição** do download (cache). Sobrou o
desperdício que nenhuma das duas resolve: **a vitrine baixa sempre o arquivo inteiro, qualquer que
seja o tamanho em que ele vai aparecer.**

Três lugares medidos:

| Onde | Tamanho na tela | O que é baixado | Desperdício |
|---|---|---|---|
| Tira de miniaturas do produto (`ProductGallery`) | **64×64 px** | o original completo | **~380×** |
| Card da grade (`ProductCard`, 4 colunas) | ~270 px de largura | o original completo | ~4,5× em área |
| Palco do produto | até 1200 px | o original | correto |

O pior caso é a tira: abrir um produto com 8 fotos baixa **os 8 arquivos originais** para desenhar
oito quadradinhos de 64 px — e são os mesmos arquivos que o palco usa, então o navegador não tem
como "baixar menos" por conta própria.

Mesmo depois da compressão da 268 (que leva a mediana para ~200 KB), abrir um produto com 8 fotos
continua sendo ~1,6 MB para mostrar uma imagem grande e oito polegares. O problema não é o peso do
arquivo — é **pedir o arquivo errado**.

Causa estrutural: `assetUrl()` (`@manto/api-client`) é concatenação pura. Ela não tem noção de
tamanho, e a constituição obriga todo arquivo servido pelo Flask a passar por ela. Ou seja: é o
ponto único onde a ausência de variantes está cristalizada — e, por isso mesmo, o ponto único onde
a solução entra sem tocar componente por componente.

## Solução

### O motor já existe

`app/catalogo/og_ops.py` é um gerador de miniatura **completo e em produção** — só que acionado
exclusivamente pela prévia de link do WhatsApp. Ele já resolve tudo que é difícil:

- escada de tentativas até caber num teto de bytes (`_ATTEMPTS`, `_MAX_BYTES`);
- cache em disco com chave `md5(RECIPE_VERSION|source_url)` — foto nova ou receita nova invalida
  sozinho;
- **dimensões gravadas no nome do arquivo**, para não reabrir o JPEG só para medi-lo;
- escrita atômica por `os.replace`, segura contra duas requisições concorrentes.

A feature é **generalizar esse motor** para aceitar `(max_px, qualidade)` e uma pasta de cache por
tamanho, em vez de escrever um segundo.

### Rota de variante

`GET /catalogo/midia/t/<largura>/<arquivo>` — variante por **caminho**, não por query string.

A largura vem de uma allowlist fechada (`128`, `320`, `640`); qualquer outro valor é 404. Sem
allowlist, a rota vira um gerador de trabalho arbitrário para quem quiser pedir 10.000 tamanhos.

### Sizes escolhidos pela tela, não por convenção

| Variante | Serve | Justificativa |
|---|---|---|
| `128` | tira de miniaturas (64 px) | 2× para telas retina |
| `320` | card da grade em telas pequenas | grade é 2 colunas no celular |
| `640` | card da grade em desktop (~270 px) | 2× do maior card |
| original | palco do produto | já é o teto de 1200 px depois da 268 |

### Frontend

`assetUrl(path, { largura })` ganha o segundo parâmetro opcional — o chokepoint que a constituição
já obriga todos a usar. Com ele:

- **tira de miniaturas**: `assetUrl(url, { largura: 128 })`;
- **card da grade**: `srcset` com 320 e 640 + `sizes` refletindo a grade real
  (`grid-cols-2 sm:grid-cols-3 lg:grid-cols-4`);
- **palco**: continua no original.

## Decisões

1. **Generalizar `og_ops`, não escrever um segundo gerador.** O motor de lá já tem cache por
   digest, dimensões no nome e escrita atômica — três coisas que um gerador novo erraria antes de
   acertar. O que muda é a assinatura (`max_px`/`qualidade`/pasta), não o miolo.

2. **Variante no CAMINHO, não em query string.** Há um CDN na frente (o `cf-cache-status` aparece
   nas respostas), e cache de CDN com query string é território de configuração — caminho é
   inequívoco. Também mantém o `immutable` da 268 válido sem ressalva: cada variante é uma URL
   própria.

3. **Allowlist fechada de larguras.** Sem ela, `/t/<qualquer número>/` é um convite para alguém
   gerar milhares de arquivos no disco de 10 GB com um laço de `curl`.

4. **Geração sob demanda, com pré-aquecimento pelo CLI.** Sob demanda é auto-curável (foto nova
   nasce com variante na primeira visita) — mas o primeiro visitante paga o custo, **numa thread do
   gunicorn**, e o incidente da feature 263 foi exatamente requisição presa segurando thread. Por
   isso a feature entrega junto um `flask warm-thumbnails` para rodar depois do deploy: as ~460
   fotos geram em lote, e nenhum visitante paga a primeira vez.

5. **Depende da 268 ter rodado.** Gerar miniatura a partir de um original de 4 MB funciona, mas
   custa decode de 4 MB por variante. A ordem certa é comprimir primeiro (`flask compress-images
   --execute`), depois aquecer as miniaturas — senão o pré-aquecimento fica lento à toa.

6. **Só a superfície pública.** O ERP interno não entra: lá a rede é boa, o volume de imagens por
   tela é baixo e o ganho não paga o risco de mexer em tela de trabalho.

7. **`width`/`height` não entram junto.** O `aspect-[4/5]` do `ProductCard` já reserva o espaço, e
   não há salto de layout a corrigir — acrescentar os atributos agora seria mexer no que não está
   quebrado. *(Se algum dia o card perder o `aspect`, aí sim.)*

8. **O original continua acessível.** A rota `/catalogo/midia/<arquivo>` não muda: o palco usa, a
   prévia de link usa, e qualquer link já compartilhado continua abrindo.

## Verificação

Script `specs/270-miniaturas-catalogo/verify_270.py` contra o `manto_local`, escrito antes do
código:

- pedir `/t/128/<foto>` devolve JPEG com largura 128 e **menos de 10% dos bytes** do original;
- a segunda chamada é servida do cache (o arquivo em disco não é reescrito — comparar `mtime`);
- largura fora da allowlist devolve **404**, não gera arquivo;
- arquivo inexistente devolve 404 sem criar entrada de cache;
- trocar a foto do item gera digest novo (a variante antiga não é servida para a foto nova);
- o cabeçalho de cache da variante é o mesmo `immutable` da 268;
- concorrência: duas gerações simultâneas do mesmo arquivo não corrompem o cache (o `os.replace`
  do motor já garante — o teste registra a garantia).

Na tela (`manto_local`, viewport desktop **e** mobile 375px), com a aba de rede aberta:

- abrir um produto com 8 fotos e conferir que a tira baixa **8 arquivos de ~5 KB**, não 8 originais;
- a grade do catálogo baixa a variante de 320 no celular e 640 no desktop (conferir pelo `srcset`
  resolvido, não pelo atributo);
- somar os bytes da página antes e depois — o número é o resultado da feature.

Portões: `npm run typecheck` limpo nos três apps, `ruff check` sem erro novo, `docs/01`, `docs/02` e
`docs/03` atualizados.

## Fora de escopo

**WebP/AVIF.** Ganho real (~30% sobre JPEG), mas exige negociação por `Accept` e duplica o cache.
Depois de medir o ganho desta feature.

**Paginação do catálogo.** `GET /api/catalogo` devolve todos os itens sem limite e a grade renderiza
todos — hoje isso é uma lista de cards com `loading="lazy"`, então o custo é o do DOM, não o da
rede. Vira problema quando o catálogo dobrar; não é o gargalo medido agora.

**As imagens do ERP interno** e o `/uploads` privado (decisão 6).

**Reprocessar o que já está no disco:** não é preciso. As variantes nascem do original, e o original
continua onde está.
