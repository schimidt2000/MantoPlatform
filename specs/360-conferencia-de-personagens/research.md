# Research — Feature 360

Tudo abaixo foi conferido contra o espelho `manto_360` (dump de produção de 24/11/2026 02h) e contra
a `main` em `cfda4cc3`.

## R1. A fila é atual? O que mudou desde 09/11

- **Decisão**: a fila é uma consulta, não uma lista guardada: `is_active`, `figurino_sheet_id IS NULL`,
  sem `catalog_characters` com `catalog_item_id = item` e sem `catalog_characters` com
  `own_item_id = item`.
- **Achado**: dos 343 itens lidos em 09/11, todos seguem pendentes pela regra antiga; 13 itens novos
  (917–933) entraram depois e foram lidos em 24/11 (`saida_27.json`). Quatro dos 343 já são a página
  própria de um personagem de outro tema (543 Moana, 557 Rapunzel, 688 Soldadinhos Verde, 843 Senhor
  do Tempo): a ficha é do personagem, então não são pendência. Fila em 24/11: **352** itens.
- **Alternativas**: guardar a fila na carga (envelhece no primeiro cadastro feito no catálogo);
  recalcular por tarefa de fundo (mais uma thread para um dado que cabe numa consulta).

## R2. Onde a leitura mora e como entra

- **Decisão**: arquivo versionado `app/admin/dados/leitura_personagens.json`, montado por
  `specs/360-…/montar_leitura.py` a partir do piloto (19 itens, bloco `TEMAS` do HTML) e das 27 saídas
  dos leitores. Entra por `POST /api/admin/catalogo/conferencia/carregar`, sem corpo, só Superadmin.
- **Idempotência**: `UNIQUE(catalog_item_id)` + `pg_advisory_xact_lock` na carga (armadilha 10 do
  `docs/00` §6). Item que já tem conferência é pulado, sempre, tenha decisão humana ou não.
- **Por que não migration de dados**: o `startCommand` roda `flask db upgrade`; qualquer surpresa no
  dado (item excluído entre o ensaio e o deploy) derrubaria a produção. A carga explícita falha com
  mensagem e nada cai.
- **Por que não upload pela tela**: seria uma superfície a mais (arquivo, validação de formato) para um
  JSON gerado por quem desenvolve. Se um dia houver leituras frequentes, vira feature.
- **Normalização no arquivo** (feita no `montar_leitura.py`, não na carga): `tipo` em minúsculas sem
  acento; `f` sempre com extensão; `ficha` vira `ficha_id` (inteiro, do prefixo "412 Coringa"); nos
  avulsos, a ficha é extraída da frase da ação ("Ligar o item direto à ficha 412 Coringa"); recorte
  inválido vira `sem_foto`.

## R3. Referências que podem ter morrido

- A foto do personagem é FK para `catalog_item_images` com `ON DELETE SET NULL`; a ficha, FK para
  `figurino_sheets` com `SET NULL`; a conferência, FK para `catalog_items` com `CASCADE`; quem
  conferiu, FK para `users` com `SET NULL`.
- **Sem relacionamento novo do lado dos models existentes**: `CatalogItem.images` usa
  `cascade="all, delete-orphan"`; um `relationship` com backref faria o ORM tentar anular a FK antes do
  banco. A exclusão continua sendo um `DELETE` simples e o banco resolve.
- Na carga, a foto é resolvida por `(item_id, nome do arquivo)`; ausente → `sem_foto_lido` + aviso.
  Ficha ausente → sem ficha + aviso. Item ausente → ignorado e listado no resumo.

## R4. Uma tela por item, não uma lista longa

- **Decisão**: fila leve (uma linha por item) + tela do item com a ação "Conferir" fixa no rodapé e
  "próximo item" calculado no servidor, respeitando `tipo` e `q` da fila.
- **Por quê**: no celular, 352 cartões com 700 recortes numa página só é rolagem sem fim e a ação
  principal some. Uma tela por item deixa o polegar no mesmo lugar e torna "parei no 80, volto no 81"
  literal. É também o padrão lista → detalhe da casa (320).
- **Paginação**: nenhuma. A fila inteira são ~400 linhas de ~150 bytes. Paginar uma lista filtrada por
  "a conferir" pularia itens a cada conferência (o conjunto encolhe).

## R5. Como mostrar o recorte

- **Decisão**: `<img loading="lazy">` posicionada dentro de uma moldura `overflow-hidden` com a
  proporção do recorte; largura da imagem `100/l × 100 %`, deslocamento `-x/l × 100 %` e
  `-y/a × 100 %` da moldura. Estilo inline só para esses quatro números.
- **Alternativa rejeitada**: recorte no servidor com Pillow (`GET …/recorte/<id>.jpg`). Daria o
  "recorte de verdade", mas isso é exatamente a feature seguinte; aqui custaria CPU e cache em disco.

## R6. Relógio

- `conferido_em`, `created_at` e `updated_at` em UTC (`datetime.utcnow`), como `fornecedores` (352) e
  `catalog_items.licenca_em` (345); o serializer entrega com `iso_sp`. Um relógio só na tabela.

## R7. Conferido trava

- Item conferido recusa escrita com **409 `codigo: "conferido"`** até `…/reabrir`. Dá semântica clara
  para a feature seguinte ("conferido = pode gravar") e evita toque acidental.
- Concorrência: a decisão é relida com `SELECT … FOR UPDATE` da conferência antes de gravar (armadilha
  26: travar e depois reler), para o "conferir" de uma pessoa não cruzar com a edição de outra.

## R8. Banco de verificação

- `manto_360` restaurado de `backups/manto_2026-11-24_0200.dump` (revisão `f353a1b2c3d4`, igual à
  produção e ao head da `main`). URL em `C:\tmp\mp360\.local-db-url`.
- A migration é aditiva e nasce vazia: não exige ensaio de migração destrutiva; o próprio `manto_360`
  recebe `flask db upgrade` e serve de ensaio.
