# Feature 297 — A luminária vira portal: vídeo leve com moldura, menu na página da tag e o recado da cliente

**Branch**: `297-nfc-moldura-e-menu` (da `main`) · **Created**: 2026-09-09 · **Status**: Rascunho ·
**Migration**: `<rev>` (aditiva — colunas novas em `nfc_tag_deliveries` e tabela de recados) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: "nos vídeos que associo a tag nfc preciso fazer o seguinte mecanismo.
Quando os usuários subirem o vídeo, automaticamente colocar uma moldura no vídeo. (…) Preciso
também mudar um pouco o ux dessa página (…) Também preciso que verifique se os vídeos estão
rodando certinhos (…) Lembrando que essa página é de acesso externo. Preciso que capriche na UI e
UX. Use animações possíveis com nosso stack."

## O pedido, nas palavras do dono *(obrigatório)*

Três pedidos e uma queixa, na ordem em que ele os fez:

1. **Moldura automática.** "Quando os usuários subirem o vídeo, automaticamente colocar uma moldura
   no vídeo. Isso é possível? No caso eu colocaria no sistema uma moldura png e ela precisaria se
   adaptar ao tamanho do vídeo pra sempre ficar na borda. Os vídeos sempre serão verticais. Ao
   subir, marcar ou desmarcar a caixinha de com moldura ou sem moldura, mas por padrão vir
   habilitada."
2. **A página deixa de ser uma tela só.** "Quando o link for acessado pela primeira vez, deve rodar
   um vídeo padrão que disponibilizarei. Então uma página com botões deve ser mostrada. Estilo
   menu. Um botão é para ver a mensagem especial (esse botão é o que leva para o vídeo com
   moldura). Um botão de acesso ao spotify (…), um botão para acessar o instagram."
3. **O recado da visitante.** "Ao entrar na mensagem especial, a pessoa pode enviar uma mensagem. A
   princípio só vamos agradecer a pessoa pela mensagem enviada e guardar essa mensagem. Associada a
   cliente e também associada ao link."
4. **A queixa, com print.** "Verifique se os vídeos estão rodando certinhos e verifique o
   funcionamento do gerenciador de vídeos dessa mesma seção, no print que te enviei mostra que não
   consigo rodar os vídeos. Preciso que verifique também se está rodando adequadamente para os
   clientes que acessam o vídeo." No print, os dez cards da aba Vídeos de `/3d/tags` mostram, todos,
   **"O vídeo não pode ser executado porque o arquivo está corrompido"**.

### O que a investigação de 09/09 encontrou *(a queixa tem causa, e não é corrupção)*

Levantamento feito no disco da produção e pela rota pública, sem tocar em `access_count`:

| O que se checou | Resultado |
|---|---|
| Os dez arquivos existem no disco do Render? | **Sim** — `instance/nfc_media/`, 42 a 147 MB cada, 980 MB no total |
| Estão corrompidos ou truncados? | **Não** — as caixas MP4 fecham exatamente no tamanho do arquivo nos dez |
| O codec é tocável pelo navegador? | **Sim** — H.264 (`avc1`) + AAC, `moov` no início, container `mp42` |
| O servidor entrega direito? | **Sim** — a rota pública devolve `206 Partial Content`, `Content-Type: video/mp4`, `Accept-Ranges: bytes` e os bytes certos |
| Então por que não toca? | **O peso.** São os arquivos crus da câmera: 1080x1920 e **2160x3840 (4K)**, de **23 a 76 Mbps** |

Um dos vídeos tem 16 segundos, 147 MB e 76 Mbps. Nenhum celular em 4G assiste a isso: **a cliente
que encosta o telefone na luminária está diante de um vídeo que ela não consegue carregar.** E o
gerenciador põe dez desses na mesma tela: o navegador tenta abrir vários decodificadores 4K de uma
vez, desiste e escreve a frase que o dono viu. O arquivo nunca esteve corrompido — está grande
demais para ser assistido.

O mesmo peso já cobra caro em outras contas: cada exibição arrasta o arquivo inteiro por uma thread
do gunicorn (o incidente de 26/08 nasceu disso), e dez vídeos já ocupam 980 MB dos 10 GB do disco.

Isso muda a natureza do pedido 1: **a moldura não é um enfeite acrescentado a um pipeline que
funciona — ela entra de carona no processamento que precisa existir de qualquer jeito.** Ao
converter o vídeo para um tamanho que o celular aguenta, aplicar a moldura na mesma passagem é
quase de graça. Um pedido paga o outro.

**Viabilidade da moldura (a pergunta literal do dono, "isso é possível?"): sim, e sem dependência
nova.** O contêiner do `manto-backend` no Render já traz `ffmpeg 5.1.9` em `/usr/bin/ffmpeg`, com
`libx264`, `aac` e os filtros `scale` e `overlay` — exatamente o necessário para redimensionar a
moldura PNG à tela do vídeo e gravá-la na borda.

## Clarifications

### Session 2026-09-09

- Q: A moldura deve ficar gravada dentro do arquivo do vídeo, ou ser desenhada por cima dele apenas
  na página? → A: Gravada no arquivo, na mesma passagem da conversão. O original guardado mantém a
  decisão reversível.
- Q: O que fazer com os dez vídeos que já estão no ar e hoje não tocam? → A: Reprocessar os dez,
  comprimindo e aplicando a moldura, a partir do arquivo atual (não há original guardado para eles).
- Q: Como o vídeo de abertura deve começar, e quando ele deve reaparecer? → A: Capa com um botão de
  início; ao toque, a abertura toca **com som desde o primeiro segundo**; só na primeira visita de
  cada aparelho.
- Q: Como a equipe fica sabendo que uma cliente deixou um recado? → A: Notificação no sino interno
  (o da feature 272, reaproveitado) e o texto do recado dentro da tag. Sem e-mail e sem tela nova.
- Q: Qual deve ser a qualidade do vídeo entregue à cliente? → A: 1080 de largura em pé, qualidade
  alta, na casa de 15 MB por 30 segundos. Uma única versão, sem player adaptativo.

## Cenários e Verificação *(obrigatório)*

### História 1 — A cliente consegue, enfim, assistir (Prioridade: P1)

A cliente encosta o celular na luminária, à noite, em 4G. O vídeo que a Manto gravou para ela
começa a tocar em poucos segundos, sem travar, e continua bonito na tela do telefone. Hoje ela vê
uma barra de carregamento que não anda.

Todo vídeo enviado passa a ser convertido para um formato que celular nenhum recusa: vertical
1080x1920, H.264 com áudio AAC, índice no início do arquivo, com peso na casa de poucos megabytes
em vez de uma centena. Uma versão mestre sem moldura é guardada junto, para que trocar ou tirar a
moldura depois não exija pedir o vídeo de volta à equipe.

**Por que esta prioridade**: é o único item que está quebrado AGORA, para quem paga. Os outros são
melhorias; este é um presente que não chega.

**Verificação**: cenários 1 e 2 do `verify_297.py` — o arquivo entregue tem no máximo 1080 de
largura, pesa uma fração do original e continua abrindo como vídeo válido.

**Cenários de aceite**:

1. **Dado** um vídeo vertical de 4K e 120 MB, **Quando** a equipe o envia para uma tag, **Então** o
   arquivo que a cliente recebe tem 1080x1920 e pesa menos de 15 MB.
2. **Dado** um vídeo já leve e dentro do padrão, **Quando** ele é enviado, **Então** o sistema não o
   degrada mais do que o necessário.
3. **Dado** um vídeo em processamento, **Quando** a cliente abre o link naquele instante, **Então**
   a página não mostra vídeo quebrado — mostra o estado de sempre, como se ainda não houvesse vídeo.

---

### História 2 — A moldura da Manto entra sozinha (Prioridade: P1)

Quem envia o vídeo não precisa saber de edição: a caixinha "Aplicar a moldura da Manto" já vem
marcada. A moldura é um PNG único, cadastrado uma vez no sistema, e se estica para a borda exata
do vídeo, qualquer que seja o tamanho dele. Quem quiser o vídeo cru desmarca a caixinha antes de
escolher o arquivo.

**Por que esta prioridade**: é o pedido principal do dono e o que dá identidade ao presente. Sai na
mesma passagem da História 1, com custo marginal.

**Verificação**: cenários 3 e 4 do `verify_297.py` — com a caixa marcada os pixels da borda mudam
em relação ao original; com ela desmarcada, não.

**Cenários de aceite**:

1. **Dado** que existe uma moldura cadastrada, **Quando** um vídeo é enviado com a caixa marcada,
   **Então** o vídeo entregue mostra a moldura encostada nas quatro bordas, sem faixa preta e sem
   corte da imagem.
2. **Dado** um vídeo enviado com a caixa desmarcada, **Quando** ele fica pronto, **Então** ele
   aparece sem moldura nenhuma.
3. **Dado** que nenhuma moldura foi cadastrada ainda, **Quando** um vídeo é enviado com a caixa
   marcada, **Então** o vídeo é entregue sem moldura e quem enviou é avisado do motivo — nunca
   perde o vídeo.
4. **Dado** um vídeo já entregue, **Quando** a equipe pede para reprocessá-lo, **Então** ele é
   refeito a partir do mestre sem moldura, e não do arquivo que já tinha uma moldura gravada.

---

### História 3 — O menu da luminária (Prioridade: P2)

A cliente encosta o celular pela primeira vez e encontra uma capa com um único convite para tocar.
Ela toca, e o vídeo de abertura começa **com som desde o primeiro segundo**, o mesmo para todas as
luminárias. Terminado ele, ou se ela pular, aparece um menu de botões grandes sobre o céu estrelado
que a página já tem: **Ver a mensagem especial**, **Ouvir no Spotify**, **Seguir no Instagram**. Nas
visitas seguintes daquele aparelho o menu abre direto, sem repetir a abertura.

A capa existe por uma razão técnica que vira vantagem: navegador de celular não deixa vídeo começar
sozinho com áudio. O toque da cliente é o que libera o som — e é também o gesto que transforma a
luminária em portal.

**Por que esta prioridade**: transforma uma tela única num lugar onde a pessoa escolhe. É a
"mudança de UX" pedida, e é onde a marca aparece.

**Verificação**: cenário 5 do `verify_297.py` (a resolução pública devolve os três destinos e o
vídeo de abertura) e conferência de tela em viewport mobile 375x812.

**Cenários de aceite**:

1. **Dado** um código acessado pela primeira vez naquele aparelho, **Quando** a página carrega,
   **Então** aparece uma capa com um único botão de início, e o toque nele faz a abertura tocar com
   som, podendo ser pulada a qualquer momento. **E dado** um aparelho que já viu a abertura,
   **Quando** a cliente volta pelo mesmo link, **Então** a página abre direto no menu.
2. **Dado** o vídeo de abertura terminado ou pulado, **Quando** o menu aparece, **Então** os três
   botões estão visíveis sem rolagem, cada um com alvo de toque de pelo menos 44px.
3. **Dado** que a pessoa toca em "Ver a mensagem especial", **Quando** a transição acontece,
   **Então** o vídeo dela abre com movimento suave e existe caminho de volta para o menu.
4. **Dado** um código inexistente ou uma tag desativada, **Quando** a página carrega, **Então** ela
   mostra o mesmo menu em modo genérico, sem "Ver a mensagem especial" e sem qualquer sinal de que
   o código existe ou não.
5. **Dado** um aparelho com "reduzir movimento" ligado, **Quando** a página abre, **Então** nada
   pisca nem desliza, e todo o conteúdo continua alcançável.

---

### História 4 — O recado da cliente (Prioridade: P2)

Depois de assistir à mensagem especial, a cliente pode escrever de volta. Ela deixa um recado, o
sistema agradece na hora, e aquele recado fica guardado ligado à tag e à cliente daquela tag. É a
primeira vez que o presente tem via de volta.

**Por que esta prioridade**: fecha o ciclo emocional do produto e cria um acervo que hoje não
existe. Depende da História 3 para ter onde morar.

**Verificação**: cenários 6, 7 e 8 do `verify_297.py` — recado gravado e lido por conexão separada,
recusa de recado vazio ou gigante, e leitura protegida por papel.

**Cenários de aceite**:

1. **Dado** o vídeo da mensagem especial aberto, **Quando** a pessoa escreve um recado e envia,
   **Então** ela vê um agradecimento imediato, sem sair da página.
2. **Dado** um recado enviado, **Quando** a equipe abre a tag no ERP, **Então** o recado está lá,
   com a data e o nome de quem escreveu (quando informado).
3. **Dado** um recado enviado numa tag ligada a uma cliente, **Quando** ele é gravado, **Então**
   fica associado tanto à tag quanto àquela cliente.
4. **Dado** um recado em branco ou acima do limite de caracteres, **Quando** a pessoa tenta enviar,
   **Então** o campo é destacado com o motivo e nada é gravado.
5. **Dado** alguém sem sessão, **Quando** tenta ler os recados pela API, **Então** recebe recusa —
   recado é conteúdo privado da cliente.

---

### História 5 — O gerenciador volta a servir para revisar (Prioridade: P3)

O Artista 3D abre a aba Vídeos e vê os vídeos tocando, em pé (hoje eles são espremidos numa moldura
deitada de 16:9), com o peso e a duração de cada um, o aviso de quais ainda estão sendo preparados
e quantos recados aquela tag recebeu.

**Por que esta prioridade**: é a tela onde a queixa apareceu. Depois das Histórias 1 e 2 ela já
volta a funcionar; aqui ela fica boa.

**Verificação**: cenário 9 do `verify_297.py` (a listagem do ERP devolve estado, peso e duração) e
conferência de tela.

**Cenários de aceite**:

1. **Dado** a aba Vídeos aberta com dez tags, **Quando** a página carrega, **Então** todos os
   players tocam e nenhum mostra erro.
2. **Dado** um vídeo vertical, **Quando** o card o exibe, **Então** ele aparece em pé, sem tarjas
   pretas laterais desproporcionais.
3. **Dado** um vídeo recém-enviado e ainda em processamento, **Quando** o card o mostra, **Então**
   há um aviso claro de "preparando" e o card se atualiza sozinho quando termina.
4. **Dado** um processamento que falhou, **Quando** a equipe abre o card, **Então** vê o motivo e um
   botão para tentar de novo.

### Casos de borda

- **`ffmpeg` some do contêiner** (o Render atualiza a imagem base e ele não está declarado em
  `render.yaml`): o vídeo é aceito e entregue como veio, com aviso registrado — nunca se perde o
  arquivo nem se derruba o upload.
- **Vídeo horizontal enviado por engano**: é aceito; a moldura se adapta à tela real dele, sem
  esticar nem cortar a imagem.
- **Dois envios seguidos para a mesma tag**: o último vence; o anterior e seus arquivos saem.
- **A cliente abre a página no meio do processamento**: vê a página sem vídeo, nunca um player
  quebrado.
- **Tag sem cliente vinculada** (estoque): o recado fica ligado só à tag.
- **Envio de recado repetido ou automatizado**: há limite de taxa e teto de tamanho.
- **Os dez vídeos que já estão no ar**: precisam ser reprocessados a partir do que existe hoje (não
  há original guardado para eles) — decisão registrada nas Premissas.
- **Disco e backup**: cada vídeo passa a ocupar duas versões leves, cerca de 30 MB no total, contra
  os 42 a 147 MB de hoje. O backup de mídia no Drive encolhe junto, o que importa porque ele já usa
  6,5 GB dos 15 GB da conta de serviço.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: Ao receber um vídeo, o sistema DEVE convertê-lo para um formato compatível com
  navegadores de celular (H.264 + AAC, índice no início), limitado a 1080 pixels de largura e a um
  peso da ordem de 15 MB por 30 segundos, sem jamais descartar o arquivo enviado. É gerada **uma
  única versão** do vídeo, sem troca de qualidade conforme a conexão.
- **FR-002**: O sistema DEVE guardar uma versão **mestre sem moldura**, na mesma qualidade da
  entregue, separada do arquivo entregue à cliente, para permitir trocar ou remover a moldura depois
  sem pedir o vídeo de volta à equipe. O arquivo cru recebido é descartado assim que a conversão
  termina bem. *(Revisado na Fase 0 do plano, decisão D4: guardar o arquivo cru de 150 MB estouraria
  a cota do backup no Drive; o mestre entrega a mesma reversibilidade por 15 MB.)*
- **FR-003**: O sistema DEVE responder ao envio imediatamente, sem prender quem enviou até o fim da
  conversão, e DEVE informar o estado de cada vídeo (preparando, pronto, falhou).
- **FR-004**: O diálogo de envio DEVE apresentar a opção "Aplicar a moldura da Manto", **marcada por
  padrão**, e respeitar a escolha feita.
- **FR-005**: O sistema DEVE permitir cadastrar uma moldura PNG com transparência, usada por todos
  os vídeos, e DEVE redimensioná-la para a tela exata de cada vídeo antes de aplicá-la.
- **FR-006**: Se a moldura não estiver cadastrada ou a conversão não for possível, o sistema DEVE
  entregar o vídeo sem moldura e registrar o motivo de forma visível para a equipe.
- **FR-007**: O sistema DEVE permitir reprocessar um vídeo já entregue, aplicando ou removendo a
  moldura, a partir do mestre sem moldura.
- **FR-008**: No primeiro acesso de cada aparelho, a página pública DEVE apresentar uma capa com um
  único botão de início; o toque nele inicia o vídeo de abertura do sistema **com áudio**, e a
  abertura DEVE ser pulável a qualquer momento. Nas visitas seguintes do mesmo aparelho a página
  DEVE abrir direto no menu, sem exibir a capa.
- **FR-009**: A página pública DEVE apresentar um menu com três destinos: a mensagem especial (só
  quando a tag tem vídeo pronto), o Spotify da Manto e o Instagram da Manto.
- **FR-010**: Os endereços do Spotify e do Instagram DEVEM viver no servidor e chegar prontos à
  página, nunca fixados no código da tela (Princípio XIV).
- **FR-011**: A visitante DEVE poder enviar um recado a partir da mensagem especial, com texto
  obrigatório e nome opcional, recebendo confirmação imediata na própria página.
- **FR-012**: O recado DEVE ser gravado associado à tag e, quando a tag tiver cliente, também à
  cliente.
- **FR-013**: O sistema DEVE recusar recado vazio ou acima do limite de caracteres, apontando o
  campo, e DEVE limitar a taxa de envio por origem.
- **FR-014**: A equipe DEVE poder ler os recados de uma tag dentro do ERP, com data e autor.
- **FR-014a**: Cada recado novo DEVE gerar uma notificação no sino interno já existente, apontando
  para a tag que o recebeu. Falha ao notificar não pode impedir a gravação do recado.
- **FR-015**: A resolução pública DEVE continuar respondendo de forma idêntica para código
  inexistente, tag desativada e tag sem vídeo — nada pode revelar a existência de um código.
- **FR-016**: O gerenciador DEVE exibir os vídeos em orientação vertical, com peso, duração, estado
  do processamento e a contagem de recados.
- **FR-017**: Toda transição da página pública (abertura, menu, mensagem, recado) DEVE ter movimento
  suave e respeitar a preferência de menos movimento do aparelho.
- **FR-018**: Os dez vídeos já entregues DEVEM ser reprocessados uma única vez, com compressão e
  moldura, a partir do arquivo que existe hoje; o arquivo anterior só é descartado depois que o novo
  estiver íntegro e tocando, e a entrega nunca fica sem vídeo durante a troca.

### Entidades *(se houver dados)*

- **Entrega da tag (existente)**: ganha o arquivo mestre sem moldura, as dimensões, a duração, o
  peso, o estado do processamento, se tem moldura e o motivo de uma eventual falha — modelo em
  `app/models.py`, migration à mão.
- **Recado (novo)**: texto, nome de quem escreveu (opcional), tag de origem, cliente associada
  (quando houver), data, e marcação de lido — modelo em `app/models.py`, migration à mão.
- **Moldura e vídeo de abertura (novo)**: dois arquivos únicos do sistema, guardados no mesmo disco
  dos vídeos e apontados pela configuração — sem tabela nova.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `POST /api/3d/nfc/<tag_id>/entregas` *(alterado — passa a aceitar a escolha da moldura)* — papéis:
  ARTISTA_3D, SUPERADMIN
- `POST /api/3d/nfc/<tag_id>/entregas/<id>/reprocessar` *(novo)* — papéis: ARTISTA_3D, SUPERADMIN
- `PUT /api/3d/nfc/moldura` e `PUT /api/3d/nfc/abertura` *(novos — cadastro dos dois arquivos do
  sistema)* — papéis: ARTISTA_3D, SUPERADMIN
- `GET /api/3d/nfc/<tag_id>/recados` *(novo)* — papéis: ARTISTA_3D, SUPERADMIN
- `POST /api/nfc/<code>/recados` *(novo)* — **público, sem login**, com limite de taxa
- `GET /api/nfc/abertura/video` *(novo)* — **público, sem login**
- `GET /api/nfc/<code>` *(alterado — payload ganha menu e abertura)* — **público, sem login**

Linhas correspondentes na tabela de `docs/01` §4.3.

## Verificação (`verify_297.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/297-nfc-moldura-e-menu/verify_297.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`.

**Atenção — o espelho está velho**: o `manto_local` desta máquina tem **1 tag NFC e nenhuma
entrega**, enquanto a produção tem 35 tags e 10 vídeos. O verify cria as próprias fixtures
descartáveis (tag, cliente, vídeo curto gerado na hora) e não depende de dado do espelho. O vídeo
de teste se gera com `libopenh264` — o ffmpeg local é LGPL e não tem `libx264` (pegadinha da 265).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | envio de vídeo 4K vertical descartável | o arquivo entregue tem largura 1080 e pesa uma fração do enviado | não |
| 2 | o arquivo entregue abre como vídeo válido e é servido com `206` e `video/mp4` | a cliente consegue tocar | não |
| 3 | envio com moldura marcada | os pixels da borda diferem do original; o miolo continua igual | não |
| 4 | envio com moldura desmarcada | o vídeo entregue não tem moldura | não |
| 5 | resolução pública de código válido | payload traz Spotify, Instagram, vídeo de abertura e a mensagem só quando pronta | não |
| 6 | recado enviado pela rota pública | gravado com tag e cliente, conferido por **conexão separada**, e o sino interno recebeu a notificação correspondente | não |
| 7 | recado vazio e recado acima do limite | recusa com o campo apontado, nada gravado | **sim** |
| 8 | leitura dos recados sem sessão e com papel sem permissão | 401/403 | **sim** |
| 9 | listagem do ERP | devolve estado do processamento, peso e duração | não |
| 10 | código inexistente, tag desativada e tag sem vídeo | as três respostas são idênticas entre si | não |
| 11 | resolução pública durante o processamento | não expõe vídeo pela metade | não |
| 12 | limpeza | tag, cliente, entregas, recados, arquivos e usuário descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela: `/nfc/<code>` no Browser pane em **viewport mobile 375x812** (abertura, menu,
mensagem, envio de recado, volta ao menu, e a variante com "reduzir movimento" ligado) e
`/3d/tags?aba=videos` no ERP (dez cards tocando, vídeo em pé, estado do processamento).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: um vídeo de 30 segundos entregue à cliente pesa no máximo 15 MB (hoje: até 147 MB) e
  começa a tocar em até 3 segundos numa conexão de celular comum.
- **SC-002**: os dez vídeos já existentes tocam, sem erro, na aba Vídeos do ERP e no link público.
- **SC-003**: quem envia um vídeo recebe resposta em até 5 segundos, e o vídeo fica pronto em até 5
  minutos, com o estado visível o tempo todo.
- **SC-004**: 100% dos vídeos enviados sem intervenção saem com a moldura aplicada, e desmarcar a
  moldura custa um único clique.
- **SC-005**: a visitante alcança qualquer um dos três destinos do menu com um toque, e chega ao
  menu em no máximo dois.
- **SC-006**: nenhuma resposta pública permite distinguir código inexistente, tag desativada e tag
  sem vídeo (invariante herdada da feature 255).
- **SC-007**: o espaço ocupado pelos vídeos no disco cai pelo menos 70% depois do reprocessamento
  dos dez existentes, de 980 MB para menos de 300 MB, já contando mestre e entregue de cada um.
- **SC-008**: nenhum recado enviado se perde: todo envio confirmado em tela aparece no ERP.

## Fora de escopo

- Campanhas por tag (o gancho `campaign` continua nulo) e mais de uma entrega por tag.
- Moldura diferente por evento, por produto ou por cliente — é uma moldura só, do sistema.
- Responder ao recado pelo sistema, notificar por e-mail, ou criar uma tela própria de recados — o
  aviso é o sino interno que já existe, e o texto mora dentro da tag (decisão de 09/09).
- Duas versões do mesmo vídeo com troca de qualidade conforme a conexão (decisão de 09/09).
- Player próprio (controles customizados), legendas, miniatura de vídeo (poster).
- Servir vídeo por CDN ou armazenamento externo; o disco do Render continua sendo a casa.
- Mudar a URL gravada na tag física — `/nfc/<code>` é imutável e eterna.
- Healthcheck do `manto-frontend` e demais pendências operacionais da 296.

## Docs a atualizar

`docs/01` §4.3 (as sete linhas de RBAC) e §5.3 (o que passa a morar no disco), `docs/02` (a página
pública `/nfc/<code>` reescrita e a aba Vídeos de `/3d/tags`), `docs/03` (entrada 297 no topo),
`docs/00` §6 (a pegadinha do vídeo cru de câmera e a do `ffmpeg` não declarado), `docs/05` (dívida
nova: `ffmpeg` é dependência de fato e não está no `render.yaml`).

## Premissas

Defaults assumidos onde o pedido não disse. Os cinco primeiros foram **confirmados pelo dono em
09/09** e estão registrados em "Clarifications"; os demais seguem como default desta spec.

1. **A moldura é gravada no arquivo**, não sobreposta pela página — *confirmado pelo dono em
   09/09*. É a leitura literal de "colocar uma moldura no vídeo", e sai de graça na conversão que a
   História 1 já exige. O original fica guardado, então a decisão é reversível: trocar a moldura
   depois é reprocessar, não regravar.
2. **Os dez vídeos já no ar serão reprocessados**, comprimidos e com moldura — *confirmado pelo dono
   em 09/09*. Como não existe original guardado para eles, o reprocessamento parte do arquivo atual:
   perde-se um pouco de qualidade, ganha-se um vídeo que a cliente consegue ver. Vira FR-018.
3. **A abertura começa por um toque na capa e toca com som**, uma vez por aparelho, e é a mesma para
   todas as luminárias — *confirmado pelo dono em 09/09*. Quem volta cai direto no menu. A memória
   de "já viu" mora no próprio aparelho, então trocar de telefone ou limpar os dados do navegador
   faz a abertura aparecer de novo. Isso é aceito.
4. **O recado avisa pelo sino interno** que a feature 272 já construiu, e o texto fica dentro da tag
   — *confirmado pelo dono em 09/09*. Sem e-mail e sem tela nova de recados.
5. **O vídeo entregue é uma versão única, de 1080 de largura e qualidade alta**, na casa de 15 MB
   por 30 segundos — *confirmado pelo dono em 09/09*. Sem troca de qualidade conforme a conexão.
6. O recado pede **texto (obrigatório) e nome (opcional)**; não pede e-mail nem telefone — menos
   dado pessoal guardado, menos atrito para escrever.
7. A moldura e o vídeo de abertura são cadastrados **dentro da própria tela `/3d/tags`**, por quem
   já cuida das tags, e não numa tela de configuração nova.
8. O endereço do Spotify é o que o dono mandou; o do Instagram é o que já existe no sistema
   (`MANTO_INSTAGRAM_URL`), e passa a viajar no payload junto com o novo.
9. O limite de 250 MB por envio continua valendo, agora medindo o arquivo **recebido** — o entregue
   será muito menor.
10. A conversão roda no próprio serviço do backend, em segundo plano, com no máximo um vídeo por
    vez, para não competir com o ERP. O `ffmpeg` já está no contêiner.
