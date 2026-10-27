# Feature 320 — Voltar sem perder o lugar (catálogo, banco de talentos e arquivos no app instalado)

**Branch**: `320-voltar-sem-perder-o-lugar` (da `main`, worktree `C:\tmp\mp320`) · **Created**: 2026-10-27 ·
**Status**: PRONTA, aguardando deploy · **Migration**: nenhuma · **Nível**: 1 (feature) — constituição, Princípio VI
(três superfícies: app interno, catálogo público e todas as telas que abrem arquivo)

**Input**: pedido do dono: "ao voltar a página no catálogo e no banco de talentos, eu não volto
exatamente para a página onde eu estava. volta para o início […] quando faço uma pesquisa no
catálogo, entro em um tema, aí clico para voltar, eu saio da página onde eu estava e volta para o
início, ou seja, perco o fio da meada. mesma coisa no banco de talentos. e também precisava de uma
forma de retornar à página anterior quando abro um comprovante dos gastos extras, por exemplo. Pois
a maioria das pessoas usa a forma de abrir um link do navegador como app. aí quando abre o
comprovante, eu tenho que fechar o app para conseguir voltar a usar."

## O pedido, nas palavras do dono *(obrigatório)*

Três sintomas com a mesma raiz — "voltar" não devolve a pessoa para onde ela estava:

1. **Catálogo**: a pessoa pesquisa (ou escolhe uma categoria), rola a lista, entra num tema e volta.
   Cai no topo da lista, com a busca apagada. Precisa refazer a pesquisa e reencontrar o ponto.
2. **Banco de talentos**: o mesmo — a pesquisa, os filtros, a aba (ativos/pendentes) e a página se
   perdem ao voltar de uma ficha.
3. **Arquivo aberto no app instalado**: a equipe usa o sistema pelo **iPhone**, com o ícone na Tela
   de Início ("como app", sem a barra do Safari). Ao tocar em "Ver" num comprovante (ex.: gastos
   extras), o arquivo abre fora do sistema e não há botão para voltar; a pessoa fecha o app.

Respostas do dono em 27/10/2026: consertar **os dois catálogos** (o catálogo de personagens que abre
pelo menu "Catálogo" e o gerenciador em Admin → Catálogo); o aparelho é o **iPhone**; o visualizador
vale para **todo arquivo aberto no app interno**, não só para comprovantes.

## Clarifications

### Session 2026-10-27

- Q: Qual catálogo perde o lugar ao voltar — o de personagens (menu "Catálogo") ou o gerenciador
  (Admin → Catálogo)? → A: Os dois.
- Q: Em que aparelho a equipe usa o sistema "como app", sem a barra do navegador? → A: iPhone
  (ícone na Tela de Início).
- Q: O visualizador de arquivo vale só para comprovantes de gastos extras ou para todo arquivo do
  app interno? → A: Todo arquivo aberto no app interno.

## Cenários e Verificação *(obrigatório)*

### História 1 — Voltar ao catálogo no mesmo ponto (Prioridade: P1)

A comercial abre o catálogo de personagens, digita "princesa", escolhe a categoria "Shows", rola até
o meio da lista e toca num tema. Lê o tema e volta (pelo "← Voltar ao catálogo" ou pelo gesto/botão
de voltar). Encontra a lista como deixou: "princesa" na busca, "Shows" selecionada e a rolagem no
tema que ela abriu. O mesmo vale para o gerenciador interno (Admin → Catálogo): busca, categoria,
situação e modo de visualização voltam como estavam, e a rolagem também.

**Por que esta prioridade**: é o uso diário da comercial durante o atendimento; perder o ponto a cada
tema multiplica o tempo de cada orçamento.

**Verificação**: cenários 1 a 4 do `verify_320.py`.

**Cenários de aceite**:

1. **Dado** o catálogo de personagens com busca "princesa" e uma categoria escolhida, rolado até um
   card no meio da lista, **Quando** a pessoa abre o tema e volta pelo "← Voltar ao catálogo",
   **Então** a busca e a categoria continuam as mesmas e o card aberto está visível na tela.
2. **Dado** o mesmo estado, **Quando** a pessoa volta pelo voltar do navegador/gesto, **Então** o
   resultado é o mesmo do cenário 1.
3. **Dado** um link do catálogo com busca e categoria copiado e aberto em outro aparelho, **Quando**
   a página carrega, **Então** a lista já aparece filtrada (a busca vive no endereço).
4. **Dado** o gerenciador interno filtrado (busca + categoria + situação) e rolado, **Quando** a pessoa
   abre um item para editar (pelo card ou pelo menu "Editar") e volta (pelo link "Voltar", depois de
   salvar, ou pelo voltar do navegador), **Então** os filtros e a rolagem são os de antes.
5. **Dado** que a pessoa chegou a um tema por um link direto (sem ter passado pela lista), **Quando**
   toca em "← Voltar ao catálogo", **Então** vai para o início do catálogo (não sai do site).

---

### História 2 — Voltar ao banco de talentos no mesmo ponto (Prioridade: P1)

O casting abre o banco de talentos, troca para "Pendentes", pesquisa "palhaço", aplica filtros, vai
para a página 3 e abre uma ficha. Ao voltar (pelo atalho da ficha ou pelo voltar do navegador),
encontra a aba, a pesquisa, os filtros, a página e a rolagem como estavam.

**Por que esta prioridade**: mesmo problema, mesma frequência, outro time.

**Verificação**: cenários 5 e 6 do `verify_320.py`.

**Cenários de aceite**:

1. **Dado** o banco de talentos com aba, pesquisa, filtros e página escolhidos e rolado até um talento,
   **Quando** a pessoa abre a ficha e volta, **Então** tudo está como antes e o talento aberto está
   visível.
2. **Dado** a ficha de um talento pendente, **Quando** a pessoa usa o atalho para os pendentes (ou
   rejeita o cadastro e é levada de volta), **Então** a lista abre na aba "Pendentes" (hoje abre em
   "Ativos").

---

### História 3 — Arquivo abre dentro do sistema, com "Voltar" (Prioridade: P1)

No iPhone, com o sistema aberto pelo ícone da Tela de Início, a pessoa toca em "Ver" num comprovante
de gasto extra. O arquivo abre por cima da tela, dentro do sistema, com um botão "Voltar" sempre à
vista. Foto aparece inteira e pode ser ampliada com os dedos; PDF aparece com todas as páginas,
roláveis. Ao tocar em "Voltar" (ou no voltar do navegador), a pessoa está na mesma tela, no mesmo
ponto. Um botão "Baixar" continua permitindo salvar ou compartilhar o arquivo. Vale para todo lugar
do app interno que abre um arquivo (comprovantes, notas, contratos, documentos do talento, anexos do
evento, figurino, revisão de vídeo, formulários).

**Por que esta prioridade**: hoje a pessoa precisa fechar o app — perde o que estava fazendo.

**Verificação**: cenários 7 a 9 do `verify_320.py` (viewport de iPhone).

**Cenários de aceite**:

1. **Dado** a tela de gastos extras com um comprovante em foto, **Quando** a pessoa toca em "Ver",
   **Então** a foto aparece por cima da tela, dentro do sistema, com "Voltar" visível, e o endereço
   do sistema não muda de site.
2. **Dado** um comprovante em PDF, **Quando** a pessoa toca em "Ver", **Então** as páginas do PDF
   aparecem dentro do sistema, roláveis, com "Voltar" visível.
3. **Dado** o arquivo aberto, **Quando** a pessoa toca em "Voltar" ou usa o voltar do navegador,
   **Então** o arquivo fecha e a tela de antes aparece no mesmo ponto de rolagem.
4. **Dado** um arquivo que o sistema não sabe mostrar (planilha, documento do Word, áudio), **Quando**
   a pessoa toca em "Ver", **Então** o visualizador diz que esse tipo de arquivo não tem prévia e
   oferece "Baixar", ainda com "Voltar".
5. **Dado** um arquivo que não carrega (apagado ou sem permissão), **Quando** a pessoa toca em "Ver",
   **Então** aparece a mensagem de erro no padrão da casa, com "Voltar".

---

### História 4 — Catálogo aberto pelo menu não prende quem usa o app (Prioridade: P2)

No app instalado, o item "Catálogo" do menu hoje abre o catálogo fora do sistema, com a mesma
armadilha do comprovante. No app instalado, o catálogo passa a abrir na mesma janela e mostra um
"← Voltar ao sistema" que devolve a pessoa à tela de onde ela saiu. No navegador comum nada muda (o
catálogo segue abrindo em outra aba), e a cliente que abre o catálogo pelo link nunca vê esse botão.

**Por que esta prioridade**: é a mesma armadilha da História 3, num caminho que a comercial usa
para chegar ao catálogo; vem depois porque a pessoa pode abrir o catálogo por outros caminhos.

**Verificação**: cenário 10 do `verify_320.py` (modo app instalado simulado).

**Cenários de aceite**:

1. **Dado** o sistema aberto como app instalado, **Quando** a pessoa toca em "Catálogo" no menu,
   **Então** o catálogo abre na mesma janela com "← Voltar ao sistema" visível.
2. **Dado** o catálogo aberto assim, **Quando** a pessoa toca em "← Voltar ao sistema", **Então**
   volta à tela interna de onde saiu.
3. **Dado** o catálogo aberto no navegador comum (cliente ou equipe), **Quando** a página carrega,
   **Então** não há "← Voltar ao sistema".

### Casos de borda

- **Lista que mudou enquanto a pessoa estava fora** (talento aprovado, tema excluído, item que saiu
  do filtro): a lista volta com os mesmos filtros; se o ponto exato não existe mais, a rolagem vai
  para o mais perto possível, sem erro.
- **Lista ainda carregando ao voltar** (cache expirado): a rolagem é aplicada quando a lista termina
  de carregar, não antes (senão cai no topo de novo).
- **Página de talentos que deixou de existir** (a pessoa estava na página 5 e agora há 4): a lista
  mostra a última página existente.
- **Entrar na lista pelo menu** (navegação nova, não "voltar"): começa do topo, com os filtros do
  endereço — "voltar" restaura, "ir" começa limpo.
- **Recarregar a página da lista**: busca e filtros continuam (estão no endereço).
- **Arquivo enorme** (PDF de muitas páginas): o visualizador mostra as páginas aos poucos e não
  trava a tela.
- **Visualizador aberto e a pessoa recarrega a página**: a tela volta sem o visualizador aberto (sem
  erro).
- **Teclado/desktop**: "Esc" fecha o visualizador; foco volta ao botão "Ver" que o abriu.
- **Botão "Ver" dentro de um diálogo** (ex.: adiantamentos na Planilha de Pagamentos): o visualizador
  abre por cima do diálogo e, ao fechar, o diálogo continua aberto.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Listas (Histórias 1 e 2)**

- **FR-001**: A busca, a categoria e os demais filtros do catálogo de personagens DEVEM ficar no
  endereço da página, de modo que voltar, recarregar ou abrir o link reproduza a mesma lista.
- **FR-002**: A busca, a categoria, a situação e o modo de visualização do gerenciador de catálogo
  DEVEM ficar no endereço da página (o modo de visualização continua lembrado entre visitas quando
  o endereço não diz qual é).
- **FR-003**: A aba (ativos/pendentes/e-mails com problema), a pesquisa, os filtros, a visualização e a página do banco de
  talentos DEVEM ficar no endereço da página; o endereço `?status=pending`, que a ficha já usa, DEVE
  abrir a aba "Pendentes".
- **FR-004**: Ao voltar para uma dessas três listas (no catálogo público, também a página de uma categoria), o sistema DEVE devolver a rolagem ao ponto em
  que a pessoa estava, depois que a lista terminar de aparecer.
- **FR-005**: Ao chegar numa dessas listas por navegação nova (menu, link), a rolagem DEVE começar
  do topo.
- **FR-006**: Os atalhos "Voltar"/"← Voltar ao catálogo" das páginas de detalhe (tema público,
  categoria pública, edição no gerenciador, ficha de talento) DEVEM se comportar como o voltar do
  navegador quando a pessoa veio da lista; quando ela chegou por link direto, DEVEM levar ao início
  da lista.
- **FR-007**: Salvar uma edição no gerenciador de catálogo DEVE devolver a pessoa à lista com os
  filtros e a rolagem de antes.
- **FR-008**: Digitar na busca NÃO DEVE criar um passo de "voltar" por letra: voltar da lista leva à
  tela anterior à lista, não à busca de uma letra atrás.

**Visualizador de arquivo (História 3)**

- **FR-009**: Todo "Ver"/link de arquivo guardado no sistema (enviado pela equipe ou pelo talento) no
  app interno DEVE abrir o arquivo num visualizador dentro do sistema, por cima da tela atual, sem
  trocar de página nem abrir outra janela. Links para outros sites (comprovante da InfinitePay,
  Drive, ClickSign, WhatsApp, Maps) seguem abrindo fora, como hoje.
- **FR-010**: O visualizador DEVE mostrar foto (JPG, PNG, WEBP, GIF, HEIC já convertido pelo
  servidor) e PDF (todas as páginas, roláveis) — inclusive no iPhone com o sistema aberto como app.
- **FR-011**: O visualizador DEVE ter "Voltar" sempre visível (fora da área que rola) e DEVE fechar
  também pelo voltar do navegador/gesto e pela tecla Esc, devolvendo a pessoa ao mesmo ponto da tela.
- **FR-012**: O visualizador DEVE oferecer "Baixar" (salvar/compartilhar o arquivo) para todo tipo.
  No iPhone, "Baixar" NÃO PODE abrir o arquivo na janela do sistema (seria a mesma armadilha): abre
  a opção do aparelho de salvar ou compartilhar, e a pessoa continua no visualizador.
- **FR-013**: Tipo sem prévia (planilha, Word, áudio, vídeo, outros) DEVE mostrar o nome do arquivo,
  a frase de que não há prévia para esse tipo e "Baixar".
- **FR-014**: Falha ao carregar o arquivo DEVE mostrar "Não foi possível abrir o arquivo. Tente
  novamente." com "Tentar novamente" e "Voltar".
- **FR-015**: O endereço de todo arquivo aberto pelo visualizador DEVE passar pela regra única de
  endereço de arquivo do projeto (hoje o comprovante de gasto extra usa o caminho cru).

**Catálogo pelo menu no app instalado (História 4)**

- **FR-016**: Com o sistema aberto como app instalado, o item "Catálogo" do menu DEVE abrir o
  catálogo na mesma janela; no navegador comum, continua abrindo em outra aba.
- **FR-017**: O catálogo de personagens, quando aberto como app instalado, DEVE mostrar
  "← Voltar ao sistema", que devolve a pessoa à tela interna de onde saiu (ou ao início do sistema,
  se não houver de onde voltar). Fora do app instalado o botão NÃO aparece.

**Gerais**

- **FR-018**: Nenhum texto novo foge do tom e do glossário da constituição §XV ("Ver", "Baixar",
  "Voltar", "Tentar novamente"; interno operacional, público lúdico e claro).
- **FR-019**: Nenhuma permissão muda: o visualizador só mostra o que o link já mostrava (o arquivo
  continua exigindo login como hoje).

### Entidades

Nenhuma. Não há dado novo nem mudança no banco.

### RBAC

Nenhum endpoint novo ou alterado. Os arquivos continuam servidos por `/uploads/<caminho>` com login
obrigatório (`app/__init__.py`), e o visualizador abre a mesma URL que o link abria.

## Verificação (`verify_320.py`) *(obrigatório — Princípio VIII)*

A feature é 100% de navegador (histórico, rolagem, sobreposição): não há regra de negócio no Flask
para o `test_client` exercitar. O `verify_320.py` cria um usuário descartável, escolhe os dados e
entrega a navegação ao `verify_320_navegador.mjs`, que roda num navegador de verdade com o Playwright
que já está em `frontend/node_modules` (feature 180), contra o Vite + Flask sobre `manto_local`.
Login **só** por `POST /api/auth/login`; as únicas escritas são o usuário descartável e dois
gastos extras descartáveis com comprovante (foto e PDF que existem no disco local), apagados no
`finally`. Viewport de iPhone (390×844, toque) nos cenários do visualizador e do app instalado.
Desvio registrado no Rastreamento de complexidade do `plan.md`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Catálogo público: busca + categoria, rola, abre tema, "← Voltar ao catálogo" | busca, categoria e card aberto visíveis | não |
| 2 | Idem, voltando pelo histórico do navegador | mesmo resultado | não |
| 3 | Catálogo público aberto direto num endereço com busca/categoria | lista já filtrada | não |
| 4 | Gerenciador: filtros + rolagem → editar pelo card ("‹ Catálogo") e pelo menu "Editar" (voltar do navegador) | filtros e rolagem de antes (o pós-salvar usa o mesmo `useVoltarParaLista` e não é exercitado: escreveria no catálogo) | não |
| 5 | Talentos: aba + pesquisa + filtro + página + rolagem → ficha → voltar | tudo como antes | não |
| 6 | Talentos: `/talents?status=pending` | abre em "Pendentes" | não |
| 7 | Gastos extras (iPhone): "Ver" em comprovante foto e em PDF | visualizador dentro do sistema; mesma URL de página; "Voltar" visível; PDF com páginas desenhadas | não |
| 8 | Visualizador: "Voltar" e voltar do navegador | fecha; rolagem da tela igual à de antes | não |
| 9 | Varredura do app interno | nenhum link de arquivo (`/uploads/`, `target="_blank"` para arquivo) fora do visualizador nas telas da História 3 | não |
| 10 | App instalado simulado: menu "Catálogo" → "← Voltar ao sistema"; navegador comum sem o botão | abre na mesma janela e volta; cliente não vê o botão | não |
| 11 | Navegação nova pelo menu para a lista já visitada | começa do topo (não restaura indevidamente) | não |
| 12 | Contraprova na `main` | cenários 1, 5 e 7 **falham** no código de antes | **sim** |

Conferência de tela: catálogo público, gerenciador, banco de talentos, gastos extras com o
visualizador (foto e PDF) e um diálogo com "Ver" (adiantamentos) no Browser pane, em viewport de
iPhone; o visualizador também em desktop (Esc e foco).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Em 100% das voltas de um tema/ficha para a lista (catálogo público, gerenciador, banco
  de talentos), a pessoa encontra a mesma busca e os mesmos filtros e vê na tela o item que abriu,
  sem rolar.
- **SC-002**: Reencontrar o ponto da lista depois de ver um tema leva zero toques além do "voltar"
  (hoje: refazer a busca, reaplicar filtros e rolar).
- **SC-003**: No iPhone com o sistema aberto pelo ícone da Tela de Início, abrir e fechar um
  comprovante nunca exige fechar o app: 100% das telas que abrem arquivo no app interno usam o
  visualizador.
- **SC-004**: Foto e PDF de comprovante ficam legíveis no iPhone sem sair do sistema (todas as páginas
  do PDF acessíveis).

## Fora de escopo

- Transformar o sistema num app instalável "oficial" (manifesto, ícone próprio, modo offline). Esta
  feature só faz o sistema se comportar bem quando já está aberto como app.
- Arquivos no portal do artista e no site público (exceto o "← Voltar ao sistema" do catálogo).
- Restaurar rolagem em outras listas (agenda, pagamentos, eventos). O mecanismo fica pronto para
  reuso; aplicar em outras telas é pedido novo.
- Editar ou anotar arquivo no visualizador; girar foto; imprimir pelo visualizador.
- Links para documentos fora do sistema (Google Drive, ClickSign): continuam abrindo fora.
- O botão "imprimir" da lista de figurinos (abre uma página de impressão, não um arquivo).
- Links do gerenciador para outras telas (visão Personagens → figurino) e o "Abrir página ↗" do
  personagem: seguem como estão.
- Links de página pública abertos do interno (formulário "Abrir", página do personagem): não são
  arquivo; no app instalado continuam abrindo fora (pedido novo, se incomodar).

## Docs a atualizar

`docs/02` (catálogo público, gerenciador, banco de talentos e o visualizador de arquivo como padrão
de tela), `docs/03` (entrada no topo), `docs/00` §5 (convenção nova: estado de lista no endereço +
arquivo sempre pelo visualizador) e `docs/05` (risque/registre dívidas: e2e da feature 180 parado,
links de arquivo crus).

## Premissas

- A equipe usa o iPhone em versão recente do iOS, com o sistema adicionado à Tela de Início, que abre
  sem a barra do Safari. O sistema não tem manifesto de app; o comportamento "como app" vem do iOS.
- "Voltar" no visualizador deve funcionar também pelo gesto de voltar do iPhone quando ele existir.
- Comprovantes são, na prática, fotos do celular e PDFs de banco; outros tipos são raros e ficam com
  "Baixar".
- Os arquivos são servidos pelo mesmo endereço do sistema e com login; o visualizador não precisa de
  permissão nova.
- Fotos HEIC já chegam convertidas pelo servidor (features 292/293).
