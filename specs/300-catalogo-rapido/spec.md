# Feature 300 — Catálogo rápido: a tela abre sem ficar esperando

**Branch**: `300-catalogo-rapido` (da `main`) · **Created**: 2026-09-16 · **Status**: Rascunho ·
**Migration**: nenhuma · **Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: *"A página de gerenciamento do catálogo está extremamente lenta. Eu
preciso que você analise e, para a gente seguir com a esteira dos spec kit, resolva esse problema.
Você clica lá, demora muito para carregar, não sei se por conta das fotos."*

## O pedido, nas palavras do dono *(obrigatório)*

O sintoma como o dono viu: **clica em "Gerenciar catálogo" e a tela demora muito para carregar.**
A suspeita dele — "não sei se por conta das fotos" — está certa pela metade, e a metade que falta
é maior que a suspeitada.

Perguntado se a vitrine pública entrava junto (ela tem exatamente o mesmo defeito), o dono
respondeu **"as duas juntas"**: um deploy só.

### O que a medição encontrou (espelho `manto_local`, 458 produtos / 457 ativos / 219 personagens / 2.674 fotos)

| Onde | Consultas ao banco | Tempo do servidor | Tamanho da resposta |
|---|---|---|---|
| Gerenciador `/admin/catalogo` | **1.846** | 1,56 s | 199 KB |
| Gerenciador, visão Personagens | **474** | 854 ms | — |
| **Gerenciador, aba Personagens aberta** (dispara os dois) | **2.320** | — | — |
| Vitrine `GET /api/catalogo` | **916** | 661 ms | 193 KB |
| Vitrine, maior categoria (90 itens) | **182** | 124 ms | 37 KB |

São **duas causas independentes**, e nenhuma delas é o tamanho da resposta — 199 KB é irrisório:

1. **Uma consulta ao banco por produto, várias vezes.** Não existe carregamento antecipado em
   nenhum ponto do caminho do catálogo: cada produto da lista dispara consultas próprias para as
   categorias, as fotos, o elenco e a ficha. Como a capa é "a primeira foto", pedir a capa carrega
   a coleção inteira de fotos daquele produto. Medido de antemão, sem alterar código de produção:
   com o carregamento antecipado, **1.846 → 6** e **916 → 4** consultas, com a resposta **byte a
   byte idêntica**.
2. **Foto grande dentro de caixa pequena.** Cada capa é leve (máx. 0,5 MB — a feature 268 já
   comprimiu). O problema é que são **458 de uma vez, em tamanho original, em caixas de 32 a 64
   pixels**: 95,4 MB pedidos assim que a tela abre, sem carregamento sob demanda. A miniatura de
   128px existe desde a feature 270 e custa menos de 10% dos bytes — o gerenciador é o único lugar
   do sistema que nunca a pede.

E dois agravantes que o dono sente sem saber nomear: **abrir um produto para editar** baixa o
catálogo inteiro (os 458, com todos os personagens) só para preencher o seletor de 39 categorias; e
**digitar na busca de personagem** refaz essa varredura a cada tecla, para depois jogar fora tudo
menos 8 resultados.

### Decisão anterior que esta feature reverte, de propósito

A decisão 7 da feature 270 deixou o ERP interno fora das miniaturas, com a justificativa: *"as
telas internas mostram poucas imagens por vez e o ganho não paga o risco"*. **A premissa é falsa
nesta tela**: são 458 de uma vez, não poucas. A reversão é consciente e **vale só para as telas de
lista do catálogo** — o resto do ERP interno continua coberto pela decisão original, onde a
premissa dela continua verdadeira; e o palco do produto continua no original (decisão 9 da 270,
que segue de pé).

## Clarifications

### Session 2026-09-16

- Q: A vitrine pública tem o mesmo defeito — entra nesta feature ou fica para depois? → A: **As
  duas juntas**, num deploy só.
- Q: A reversão da decisão 7 da 270 cai só para o catálogo ou varre o ERP interno inteiro? → A:
  **Só o catálogo agora.** Nas demais telas internas a premissa da 270 ainda vale (mostram poucas
  imagens por vez); a lista delas vira dívida em `docs/05`.
- Q: Quem aquece o cache de miniaturas depois do deploy? → A: **Esta sessão roda `flask
  warm-thumbnails` por SSH no `manto-backend`, logo após o deploy**, sem push na fila.

## Cenários e Verificação *(obrigatório)*

### História 1 — O gerenciador abre sem esperar pelo servidor (Prioridade: P1)

Quem organiza o catálogo clica em "Gerenciar catálogo" e a lista aparece. Hoje o servidor gasta
1,56 s conversando com o banco 1.846 vezes antes de responder qualquer coisa; a pessoa olha para um
esqueleto cinza. Depois desta história, o servidor responde o mesmo conteúdo com um punhado de
consultas.

A tela tem **três modos** (Cards, Árvore e Personagens) e a história cobre os três. O modo
Personagens é o pior: ele pede a listagem **e** um segundo caminho próprio, que sozinho custa outras
**474 consultas** — **2.320 numa abertura**. A causa ali é a mesma (uma consulta por produto, para
um teste de verdade/falso sobre o elenco), e a cura também.

**Por que esta prioridade**: é a maior parte da espera e a que não tem contrapartida nenhuma —
o conteúdo entregue é idêntico, então não há nada a decidir nem a conferir visualmente.

**Verificação**: cenário 1 do `verify_300.py` — conta as consultas ao banco com um ouvinte de SQL e
compara a resposta com a de hoje, campo a campo.

**Cenários de aceite**:

1. **Dado** o catálogo com 458 produtos, **Quando** a lista do gerenciador é montada, **Então** o
   número de consultas ao banco não passa de 10 e não cresce com a quantidade de produtos.
2. **Dado** a resposta de hoje guardada, **Quando** a lista é montada depois da mudança, **Então**
   o conteúdo é idêntico — mesmas chaves, mesmos valores, mesma ordem.
3. **Dado** um filtro de busca, categoria ou status aplicado, **Quando** a lista é montada,
   **Então** o resultado é o mesmo de hoje e a contagem de consultas continua limitada.

---

### História 2 — A tela para de baixar foto grande para caixa pequena (Prioridade: P1)

As listas do gerenciador desenham a capa do produto e o rosto do personagem em quadradinhos de 32 a
64 pixels, mas baixam o arquivo inteiro de cada um — 95,4 MB assim que a tela abre, tudo de uma
vez. Depois desta história, cada quadradinho pede a miniatura, e as que estão fora da tela só são
pedidas quando a pessoa rola até elas.

**Por que esta prioridade**: é a outra metade da espera, e é a que o dono viu ("não sei se por conta
das fotos").

**Verificação**: cenário 2 do `verify_300.py` — prova que a miniatura pedida existe, responde e
pesa menos de 10% do original. Conferência de tela: gerenciador aberto nos três modos.

**Cenários de aceite**:

1. **Dado** a lista do gerenciador aberta, **Quando** a tela desenha as capas, **Então** o endereço
   pedido é o da miniatura, não o do arquivo original.
2. **Dado** uma lista mais longa que a tela, **Quando** a tela abre, **Então** só as imagens
   visíveis são pedidas; as demais chegam ao rolar.
3. **Dado** um produto cuja foto está no banco mas o arquivo sumiu, **Quando** a lista desenha,
   **Então** aparece o espaço reservado de sempre, nunca um quadrado quebrado.

---

### História 3 — A vitrine pública carrega com o mesmo alívio (Prioridade: P2)

A cliente abre o catálogo no celular. O servidor hoje conversa 916 vezes com o banco para montar a
grade, e duas telas ainda baixam fotos originais para espaços pequenos: a **grade de categorias** e
a **lista de desejos** (quadrado de 64px baixando o original — exatamente o desperdício de ~380×
que motivou a feature 270).

**Por que esta prioridade**: é o que a cliente vê. Vem depois das duas primeiras porque a dor
relatada é interna, e porque um engano aqui aparece para fora.

**Verificação**: cenário 3 do `verify_300.py` — contagem de consultas na grade geral e na página de
categoria, com resposta idêntica à de hoje. Conferência de tela em viewport mobile (Princípio X).

**Cenários de aceite**:

1. **Dado** a grade geral da vitrine, **Quando** é montada, **Então** o número de consultas não
   passa de 10 e a resposta é idêntica à de hoje.
2. **Dado** a maior página de categoria, **Quando** é montada, **Então** vale o mesmo limite.
3. **Dado** a grade de categorias e a lista de desejos, **Quando** desenham suas imagens, **Então**
   pedem a miniatura adequada ao tamanho em tela.
4. **Dado** a página de um produto, **Quando** a foto grande é exibida, **Então** ela continua sendo
   o arquivo original — a decisão 9 da 270 não muda.

---

### História 4 — Abrir um produto para editar não baixa o catálogo inteiro (Prioridade: P2)

Hoje, entrar na edição de um produto dispara o download dos 458 produtos com todos os personagens,
só para montar a lista de 39 categorias do formulário. Depois desta história, o formulário pede
apenas o que usa.

**Por que esta prioridade**: multiplica a espera da História 1 por cada edição, e a correção é
pequena.

**Verificação**: cenário 4 do `verify_300.py` — as categorias do formulário chegam sem carregar a
lista de produtos.

**Cenários de aceite**:

1. **Dado** a tela de edição de um produto, **Quando** ela abre, **Então** o seletor de categorias
   é preenchido sem que a lista completa de produtos seja carregada.
2. **Dado** uma categoria criada durante a edição, **Quando** ela é salva, **Então** aparece no
   seletor como aparece hoje.

---

### História 5 — Digitar na busca do elenco não varre o catálogo (Prioridade: P3)

No painel de personagens, cada tecla digitada dispara uma varredura do catálogo inteiro, cujo
resultado é descartado menos os 8 primeiros. Depois desta história, a busca espera a pessoa parar
de digitar.

**Por que esta prioridade**: afeta uma ação pontual, não a abertura da tela — mas é a mesma regra
de economia que a constituição já exige de toda busca preditiva (Princípio XII.5).

**Verificação**: esta história **não tem cenário no `verify_300.py`** — o que se prova aqui é
comportamento de navegador (quantas requisições o campo dispara), que o verify não alcança. A prova
é conferência de tela com o painel aberto, observando as requisições. *(Não confundir com o cenário
5 da tabela abaixo, que é o de RBAC e deve falhar.)*

**Cenários de aceite**:

1. **Dado** o campo de busca do painel de personagens, **Quando** alguém digita uma palavra de 6
   letras sem pausa, **Então** o servidor recebe uma consulta, não seis.
2. **Dado** uma busca em andamento, **Quando** a pessoa continua digitando, **Então** os resultados
   anteriores permanecem na tela até os novos chegarem — sem piscar.

---

### Casos de borda

- **Produto sem foto nenhuma**: a lista desenha o espaço reservado, e nenhuma miniatura é pedida.
- **Foto no banco com arquivo ausente no disco** (a recuperação pós-Railway deixou 66 casos): a
  miniatura responde "não encontrado" e a tela mostra o espaço reservado — nunca quadrado quebrado.
- **Miniatura ainda não gerada**: a primeira pessoa a pedir espera a geração. É por isso que o
  aquecimento roda logo depois do deploy (ver "Premissas").
- **Catálogo vazio ou filtro sem resultado**: a tela mostra a mensagem de lista vazia de hoje.
- **Produto com elenco grande**: a contagem de consultas continua limitada, porque o elenco é
  carregado de uma vez para todos os produtos, não um a um.
- **A geração da miniatura falha** (arquivo corrompido, formato que o decodificador recusa): a tela
  cai no espaço reservado, como faria com arquivo ausente, e nada quebrado é gravado em disco. O
  original continua acessível pelo caminho de sempre.
- **Duas pessoas pedem a mesma miniatura ainda não gerada ao mesmo tempo**: as duas recebem a
  imagem. A feature 270 já corrigiu a corrida de escrita (arquivo temporário por thread, e quem
  perde a corrida recebe a miniatura de quem ganhou) — esta feature **não pode reintroduzir** esse
  defeito.
- **Durante a janela do deploy**, com bundle antigo e servidor novo (ou o contrário): as imagens não
  quebram — o caminho do original e o da miniatura **já existem os dois em produção** desde a 270. A
  **única** coisa que quebra, por cerca de um minuto, é o endpoint novo: com o bundle novo e o
  backend antigo, `GET /api/admin/catalogo/categorias` responde **405** (o caminho só existia para
  `POST`). O formulário de edição mostra "Não foi possível carregar as categorias" com "Tentar de
  novo", e **as categorias já marcadas não se perdem** — vêm do detalhe do produto, não desta lista.
- **Texto alternativo das imagens**: permanece como está hoje (decorativo nas miniaturas de lista,
  onde o nome já aparece ao lado em texto). Esta feature não altera acessibilidade.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE montar **cada um dos três modos** do gerenciador do catálogo — Cards,
  Árvore e Personagens — com um número de consultas ao banco que **não cresce** com a quantidade de
  produtos. Isso inclui o caminho próprio da visão Personagens, hoje responsável por 474 das 2.320
  consultas daquela aba.
- **FR-002**: O sistema DEVE montar a grade geral da vitrine, a grade de categorias e a página de
  categoria sob a mesma regra do FR-001.
- **FR-003**: As respostas dessas listas DEVEM permanecer **idênticas às de hoje** — mesmas chaves,
  mesmos valores, mesma ordem, mesmos nulos. Nenhum endpoint existente muda de forma. *(O endpoint
  novo do FR-009 não conflita com isto: ele acrescenta um caminho, sem alterar nenhum dos que já
  existem.)*
- **FR-003a** *(revisto na revisão pré-deploy de 18/09/2026)*: as duas ordenações que dependiam do
  plano de consulta passam a ser **explícitas e iguais às da produção** — nomes de categoria por
  `id`, e personagens empatados em `position` desempatando pelo `id`. Medido no código da `main`
  contra o mesmo espelho: **0 de 458 produtos** mudam de ordem, e a resposta é byte a byte idêntica
  à que a produção servia. *(A primeira versão ordenava os nomes de categoria alfabeticamente, e a
  revisão adversarial pegou o custo antes do deploy: 123 produtos mudariam — e como o card da
  vitrine mostra só as 3 primeiras etiquetas, a cliente veria etiquetas diferentes.)*
- **FR-004**: Toda imagem cuja **maior dimensão renderizada seja de até 64 pixels** nas listas do
  gerenciador DEVE pedir a miniatura de 128 px — que cobre telas de densidade 2× —, nunca o arquivo
  original.
- **FR-005**: A grade de categorias e a lista de desejos da vitrine DEVEM pedir a miniatura
  adequada ao tamanho em que a imagem é exibida.
- **FR-006**: A foto grande da página de produto DEVE continuar servindo o arquivo original.
- **FR-007**: As grades de imagem do gerenciador DEVEM pedir apenas as imagens visíveis, adiando as
  demais até a rolagem. Na vitrine este comportamento **já existe** e deve ser preservado, não
  reintroduzido.
- **FR-008**: Imagem cujo arquivo não existe DEVE cair no espaço reservado padrão, nunca em imagem
  quebrada.
- **FR-009**: A tela de edição de produto DEVE obter as categorias sem carregar a lista completa de
  produtos.
- **FR-010**: **Toda busca do gerenciador que consulta o servidor** — a da tela de listagem e a do
  painel de personagens — DEVE aguardar uma pausa na digitação antes de consultar, e DEVE manter os
  resultados anteriores visíveis enquanto os novos não chegam. *(A busca da visão Personagens é
  client-side e continua instantânea de propósito: atrasá-la seria travar a digitação sem que
  nenhuma requisição fosse economizada.)*

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

**Um endpoint novo, nenhum gate afrouxado.** O gerenciador continua restrito a SUPERADMIN
(`_require_superadmin`) e a vitrine continua pública.

| Endpoint | Papéis | Observação |
|---|---|---|
| `GET /api/admin/catalogo/categorias` | SUPERADMIN | **Novo.** Devolve só a lista de categorias, para o seletor do formulário de edição (FR-009). O caminho já existe para `POST` (criar categoria) e o gate é o mesmo; linha na tabela de `docs/01` §4.3 |
| `GET /api/admin/catalogo` · `/personagens` | SUPERADMIN | inalterados — muda só como as consultas são feitas |
| `GET /api/catalogo` · `/categorias` · `/categoria/<slug>` | público | inalterados — idem |

Como a feature edita os módulos de leitura dos dois lados, o `verify_300.py` inclui um cenário que
**deve falhar** (papel sem permissão recebendo recusa no gerenciador e no endpoint novo), para
provar que o gate não afrouxou de passagem.

## Verificação (`verify_300.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/300-catalogo-rapido/verify_300.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; limpeza no `finally`.

O critério é o **número de consultas ao banco**, medido com um ouvinte de SQL — nunca o relógio: o
tempo varia com a máquina e transformaria o verify numa fonte de falso alarme.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Lista do gerenciador (com e sem filtros) **e o caminho da visão Personagens** | consultas ≤ 10 em cada, sem crescer com o volume; respostas idênticas à referência | não |
| 2 | Miniatura de uma capa real | a URL pedida pela tela responde, e pesa < 10% do original | não |
| 3 | Grade geral e maior categoria da vitrine | consultas ≤ 10 em cada; respostas idênticas | não |
| 4 | Categorias do formulário de edição | chegam sem carregar a lista de produtos | não |
| 5 | Papel sem permissão no endpoint do gerenciador | recusa (403/404) — o gate não afrouxou | **sim** |
| 6 | Foto com arquivo **ausente**, arquivo **corrompido** e largura fora da allowlist | nenhum devolve 200, e o cache não cresce com pedido inválido | não |
| 7 | Seis pedidos **simultâneos** da mesma miniatura ainda não gerada | todos recebem 200 e **os mesmos bytes** — a corrida que a 270 corrigiu não volta | não |
| 8 | limpeza | usuário descartável apagado (`roles.clear()` antes do usuário) | — |

Conferência de tela: gerenciador nos três modos (Cards, Árvore, Personagens) e a tela de edição, no
computador; vitrine — grade geral, grade de categorias, página de produto e lista de desejos — em
viewport mobile 375×812 (Princípio X).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Abrir o gerenciador do catálogo deixa de esperar pelo servidor: o tempo até a lista
  responder cai de ~1,6 s para menos de 0,2 s no espelho, com o mesmo conteúdo na tela.
- **SC-002**: Abrir a vitrine cai de ~0,66 s para menos de 0,15 s, sob a mesma medição.
- **SC-003**: O que a tela do gerenciador baixa em fotos **na primeira tela, antes de qualquer
  rolagem**, cai para menos de 10% dos 95,4 MB de hoje; o restante só é baixado ao rolar até ele.
- **SC-004**: Nenhuma informação sai da tela e nenhum número muda: quem usa vê exatamente o mesmo
  catálogo, só que sem esperar.
- **SC-005**: Digitar uma palavra na busca de personagem gera uma consulta ao servidor, não uma por
  tecla.
- **SC-006** *(acompanhamento, não portão)*: trinta dias depois do deploy, nenhum chamado novo de "o
  catálogo está lento". Quem afere é o dono, pela ausência de reclamação — é sinal de resultado, e
  não critério que trave a entrega, porque não é falseável dentro do ciclo.

## Fora de escopo

- **Paginação e rolagem infinita.** Medido que não são necessárias: com o carregamento antecipado o
  catálogo inteiro é montado em menos de 0,11 s, e a visão Personagens **precisa** da lista inteira
  para o "usar em outro tema" funcionar. A tela não muda de comportamento.
- **A foto grande da página de produto** continua no original (decisão 9 da feature 270).
- **O resto do ERP interno.** As outras telas internas que também pedem o arquivo original para
  caixa pequena — painel e Kanban de Marketing, Fila 3D, ficha do talento, tags NFC, campanhas
  virtuais — ficam de fora por decisão do dono (16/09/2026): nelas a premissa da decisão 7 da 270
  continua verdadeira, porque mostram poucas imagens por vez. A lista vai para `docs/05`, para
  quando alguém reclamar de alguma.
- **Capas de campanha virtual** (`/catalogo/midia/campanhas/<arquivo>`): não têm miniatura possível
  hoje porque o endereço tem uma pasta a mais e não casa com a regra de variante. Vai para
  `docs/05` como dívida própria.
- **Divisão do pacote JavaScript por página.** O app interno carrega todas as telas num pacote só
  (1,3 MB); isso pesa em qualquer tela, não nesta, e mexer nisso é feature própria. Registrar em
  `docs/05`.
- **Recuperar as fotos ausentes** deixadas pela migração do Railway.

## Docs a atualizar

`docs/01` §3.10 (a rota nova de categorias na tabela do gerenciador; o §4.3 já cobre o gate, porque
a view usa o `_require_superadmin()` que já está registrado para `admin_catalogo_*`, e o contrato de
cache da rota de miniatura **não muda**), `docs/02` (entrada de `/admin/catalogo` e das telas da vitrine tocadas), `docs/03`
(entrada nova no topo, append-only, registrando a reversão consciente da decisão 7 da 270),
`docs/04` (invariante: lista de catálogo carrega o acompanhamento de uma vez, nunca por item),
`docs/05` (as três dívidas novas acima).

## Premissas

- **O cache de miniaturas da PRODUÇÃO já está quente — o aquecimento virou higiene opcional**
  (corrigido em 18/09/2026). A premissa original ("cache frio, 9 arquivos") foi medida no **espelho
  local** e generalizada sem medir a produção. Conferido por SSH, somente leitura: **2.628
  variantes de 128 px para 2.715 originais (97%)** e ~460 em cada largura de capa — o
  `warm-thumbnails` da 270 já tinha feito o serviço. O risco do incidente da 263 (centenas de
  gerações numa thread do gunicorn) **não existe lá**; as ~87 que faltam, parte delas de fotos
  perdidas na migração do Railway, geram-se sob demanda sem custo relevante. Se rodar, é por SSH no
  `manto-backend`, com `MANTO_SEM_THREADS=1` e sem push na fila.
- **A largura de 128px basta para as caixas do gerenciador** (32 a 64 pixels), cobrindo telas de
  alta densidade. A vitrine usa as larguras que a feature 270 já definiu para cada grade.
- **Nada no banco muda**: sem migration, sem coluna nova, sem campo novo na resposta.
- **O espelho `manto_local` representa a produção** em volume (458 produtos) — as medições daqui
  valem lá.
- **A pausa da busca é de 300 ms**, como o `AgruparEventosDialog` já faz, mantendo o mínimo de 2
  caracteres que o painel exige hoje — a tela não passa a exigir mais do que exigia.
- **O teto de consultas do verify fica um pouco acima do medido** (6 no gerenciador, 4 na vitrine),
  não no valor exato: um teto colado no número de hoje quebraria a cada acréscimo legítimo e
  treinaria a equipe a ignorar o verify.
- **Lista vazia e filtro sem resultado** continuam mostrando exatamente a mensagem de hoje.
