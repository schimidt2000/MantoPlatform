# 304 — Loja de conversas com cara de Natal + campanha do Papai Noel

**Branch**: `304-loja-natal-papai-noel` · **Created**: 2026-10-13 · **Status**: pronta, não publicada ·
**Migration**: nenhuma · **Nível**: 2 (correção/ajuste da 205, domínio único: loja virtual)

## O pedido

> "A primeira versão será com chamadas com o Papai Noel. As pessoas vão marcar para poder ou
> mostrar a cartinha, ou pedir para o Papai Noel dar alguma mensagem para a criança. […] crie esse
> produto com o papai noel, acerte os textos do site e identidade para ficar com cores e cara de
> natal." — dono, 13/10/2026, com duas artes de marketing (pôster vertical e banner horizontal:
> verde-floresta, vermelho veludo, dourado, serifa de alto contraste).

Respostas do dono no mesmo dia:

- **Formatos**: continuam os dois da 205 — **ou** chamada ao vivo **ou** vídeo gravado, nunca os
  dois no mesmo pedido. A cartinha é "uma das opções que podem ser feitas durante a chamada" —
  texto, não campo novo.
- **Visual**: a loja inteira (`alo.*`: vitrine, campanha, pedido, e-mails) fica com cara de Natal.
  Quando as princesas entrarem, troca-se o tema.
- **Preços e agenda**: o time preenche na tela de gestão. Eu deixo a campanha criada como
  rascunho, com textos, FAQ, termos e capa.

## O que muda

1. **Tema da loja** — paleta `alo.*` no `tailwind.config.ts` do app público (mesmo arranjo do
   `lamp.*` da 255: namespace próprio, nenhum token global muda, catálogo intacto) + Playfair
   Display para os títulos. Um `LojaLayout` envolve as três rotas `/v*` e pinta a página inteira.
   Toda a copy de marca da loja mora em `lib/lojaTema.ts`: trocar de estação = trocar esse arquivo
   e a paleta.
2. **Textos** — vitrine, campanha e pedido reescritos para o Natal: os dois formatos explicados
   ("ao vivo: dá para mostrar a cartinha" × "vídeo: um recado gravado"), FAQ com cartinha e
   "não dá para juntar os dois", dicas do formulário que mudam com o formato, e nenhum pronome
   que presuma menina ("o personagem preferido **dela**").
3. **Correções achadas no mapeamento**:
   - `PedidoVirtualPage`: "Escolher outro horário" era `<a href="/v/<slug>">` sem o basename —
     em `alo.*` virava `/catalogo/v/v/<slug>` (página branca). Vira `<Link>`.
   - Botão flutuante da lista de desejos (catálogo de festa) aparecia na loja de conversas.
   - Vitrine falava em WhatsApp sem nenhum link para ele.
   - E-mails da loja saudavam o **filho** ("Olá, Maria!") num e-mail que vai para o adulto.
   - Publicar aceitava preço R$ 0,00 (a trava só olhava `None`): uma campanha criada sem preço
     iria ao ar de graça. Agora: chamada ao vivo > 0, e vídeo > 0 quando há vagas de vídeo.
4. **E-mails da loja** — cabeçalho e botão no tema, assunto sem "interação", saudação neutra.
   `_html_wrap`/`_btn` ganham parâmetros opcionais; os outros e-mails não mudam.
5. **Prévia de link** — `/catalogo/v*` (para onde `alo.*` redireciona) passa a ter `<title>` e
   Open Graph estáticos com a arte horizontal (JPEG 1200×630, < 300 KB, servido do bundle).
   Hoje o link da loja no WhatsApp sai sem imagem e com título "Manto Produções".
6. **Campanha do Papai Noel** — `criar_campanha_noel.py` (idempotente) cria o rascunho
   "Uma chamada com o Papai Noel" ligado ao personagem do catálogo, com apresentação, termos, FAQ,
   WhatsApp da empresa e a capa (pôster vertical, versionado nesta pasta). Preços ficam em 0 e a
   publicação fica travada até o time preencher.

## Verificação

- `verify_304.py` contra o `manto_local`: script cria a campanha uma vez (rodar de novo não
  duplica), capa servida pela rota pública, publicar com preço 0 é RECUSADO (cenário que deve
  falhar), publicar com preço > 0 passa; e-mails da loja saem com o tema e sem o nome da criança
  na saudação; e-mail de outro domínio continua com o cabeçalho roxo.
- `npm run typecheck`; `ruff check` nos arquivos tocados; `node --check server.js`.
- Telas abertas no Browser pane em viewport mobile (vitrine, campanha nos dois formatos, pedido).
- Prévia: requisição com UA do WhatsApp em `/catalogo/v` devolve `og:image` absoluta e o JPEG
  responde `image/jpeg`.

## Fora de escopo

- Tema por campanha (exigiria coluna nova — o dono escolheu tema da loja inteira).
- Botão "Nova campanha" do painel (`/virtuais/campanhas/nova` fica no esqueleto para sempre:
  `Number("nova")` é NaN e a tela não sabe criar). Registrado em `docs/05`; a campanha do Noel
  nasce pelo script.
- Links dos e-mails continuam em `PUBLIC_BASE_URL` (`app.*/catalogo/v/...`), que funciona.
