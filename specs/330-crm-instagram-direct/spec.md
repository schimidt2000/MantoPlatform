# Feature 330 — Instagram Direct na caixa de Conversas

**Branch**: `330-crm-instagram-direct` (da `328-crm-equipe-na-caixa`, que ainda não está na `main`: o dono adiou a
publicação em 03/11) · **Created**: 2026-11-03 · **Status**: Implementado, não publicado · **Migration**: sim, aditiva (uma coluna em
`conversas`) · **Nível**: 1 (feature)

**Input**: pedido do dono (03/11): "Começar a 2b" — a Fase 2b do `docs/PLANO_CRM_PROPRIO.md`, o Instagram Direct na
mesma caixa do WhatsApp. As duas decisões de ligação foram respondidas no mesmo dia (Clarifications).

## O pedido, nas palavras do dono *(obrigatório)*

> "3 - sim recebe direct" · "5 - 2 vendedores ao mesmo tempo. [...] Chega bastante coisa por dia." (30/10, sobre o
> Kommo, que hoje recebe o WhatsApp e o Direct)

> "Começar a 2b" (03/11)

O plano (seção 2 da tabela de fases): "WhatsApp e **Direct na mesma caixa**". O Kommo só pode ser cancelado quando o
Direct também funcionar na Plataforma.

## Clarifications

### Session 2026-11-03

- Q: Por qual caminho ligamos o Instagram Direct da Manto? → A: **Pela Página do Facebook** (a mensageria do Instagram
  pela plataforma de mensagens da Meta, com o Instagram ligado a uma Página da Manto). O acesso é do portfólio da
  empresa, como o do WhatsApp, e não vence. Enquanto testamos, o Kommo e a Plataforma recebem as mesmas mensagens; na
  virada, a Plataforma passa a ser o app principal.
- Q: Os comentários dos posts entram na caixa nesta fase? → A: **Não, só o Direct.**

## Cenários e Verificação *(obrigatório)*

### História 1 — O Direct chega na caixa (Prioridade: P1)

Quem manda mensagem para o Instagram da Manto aparece na mesma lista do WhatsApp, com o ícone do Instagram, o nome do
perfil e o @usuário. Texto, foto, vídeo, áudio, arquivo, reação, resposta a um story e menção em story chegam na
conversa. A mídia fica guardada na Plataforma (o link da Meta expira). A lista ganha o filtro "Canal": "Todos",
"WhatsApp", "Instagram".

**Por que esta prioridade**: sem receber, não há o que responder; e o Direct é metade do atendimento que hoje está no
Kommo.

**Verificação**: cenários 1 a 9 do `verify_330.py`.

**Cenários de aceite**:

1. **Dado** um aviso assinado do Instagram com uma mensagem de texto, **Quando** ele chega, **Então** nasce uma conversa
   do canal Instagram com o nome e o @usuário do perfil, a mensagem e a espera aberta.
2. **Dado** o mesmo aviso reenviado pela Meta, **Quando** ele chega de novo, **Então** nada se repete.
3. **Dado** uma foto no Direct, **Quando** o aviso é processado, **Então** a foto é baixada pelo link do anexo e fica
   guardada na conversa.
4. **Dado** um aviso com assinatura errada, **Quando** ele chega, **Então** é recusado e nada é gravado.
5. **Dado** que a cliente apaga a mensagem, **Quando** o aviso chega, **Então** a conversa mostra "Mensagem apagada pela
   cliente." no lugar dela.
6. **Dado** que a cliente viu a resposta, **Quando** chega o aviso de visto, **Então** a mensagem enviada fica "lida".

### História 2 — Responder pelo Direct (Prioridade: P1)

A equipe responde a conversa do Instagram como responde a do WhatsApp: texto, respostas rápidas, foto, vídeo, PDF e
áudio gravado. Responsável, espera, alerta de 15 min e notas internas da 328 valem igual. A regra da janela é a do
Instagram:
- até 24 horas depois da última mensagem da cliente, a resposta sai normalmente;
- de 24 horas a 7 dias, ela sai como **resposta da equipe** (a marca de atendimento humano da Meta);
- depois de 7 dias, a caixa avisa que só a cliente pode retomar a conversa.

O Instagram não tem modelos aprovados.

**Por que esta prioridade**: receber sem responder obriga a equipe a voltar para o Kommo.

**Verificação**: cenários 10 a 17.

**Cenários de aceite**:

1. **Dado** uma conversa do Instagram com a janela aberta, **Quando** a Ana responde, **Então** a mensagem vai para a
   Meta com o id da cliente, volta com o id da Meta, a Ana vira a responsável e a espera termina.
2. **Dado** a última mensagem da cliente há 30 horas, **Quando** a Bia responde, **Então** a mensagem sai com a marca de
   resposta da equipe.
3. **Dado** a última mensagem da cliente há 8 dias, **Quando** alguém tenta responder, **Então** o envio é recusado
   com "Passaram 7 dias desde a última mensagem da cliente. Só ela pode retomar a conversa pelo Instagram.".
4. **Dado** um áudio gravado no Chrome (webm), **Quando** ele é enviado para o Instagram, **Então** sai convertido para
   m4a (o Instagram não aceita webm nem ogg em áudio).
5. **Dado** um arquivo que o Instagram não aceita (planilha, por exemplo), **Quando** alguém tenta enviar, **Então**
   é recusado na hora, apontando o arquivo.

### História 3 — Piloto ao lado do Kommo, sem duplicar (Prioridade: P2)

Durante os testes, o Kommo e a Plataforma recebem as mesmas mensagens. O que a equipe responder pelo Kommo ou pelo app
do Instagram aparece na Plataforma como "Enviada por outro app" (eco), sem duplicar o que a própria Plataforma enviou.
A Plataforma nunca responde sozinha. Sem as chaves do Instagram, o canal fica desligado e a caixa segue só com o
WhatsApp.

**Verificação**: cenários 18 a 22.

**Cenários de aceite**:

1. **Dado** um eco de mensagem que a equipe mandou pelo app do Instagram, **Quando** ele chega, **Então** aparece como
   enviada por outro app, encerra a espera e não muda o responsável.
2. **Dado** o eco de uma mensagem que a própria Plataforma enviou, **Quando** ele chega, **Então** não vira uma segunda
   mensagem.
3. **Dado** que as chaves do Instagram não estão configuradas, **Quando** chega um aviso do Instagram, **Então** ele é
   recusado (404) e a lista não oferece o filtro do Instagram.

### Casos de borda

- **Mídia efêmera ou de story.** O anexo efêmero não traz link: a conversa diz "Mídia temporária. Abra no Instagram
  para ver.". A resposta a um story e a menção em story mostram "Respondeu ao seu story" / "Mencionou a Manto no
  story", com o link quando houver.
- **Publicação compartilhada ou reels.** Aparece "Compartilhou uma publicação" (ou um reels), com o link.
- **Mensagem não suportada** pela API: "Mensagem de um tipo que a Plataforma ainda não exibe. Abra no Instagram para
  ver.".
- **Perfil indisponível.** Se o nome não vier, a conversa mostra "Contato do Instagram" e tenta de novo depois, no
  máximo uma vez por dia.
- **Pasta de Solicitações.** Mensagens que ficam paradas mais de 30 dias nas Solicitações a Meta não entrega. Não há o
  que fazer na Plataforma (premissa).
- **Marca de resposta da equipe recusada.** Se a Meta ainda não liberou essa permissão para o app, a mensagem fica "não
  entregue" com o motivo, e a caixa continua aberta para o próximo dia útil.
- **Tamanhos do Instagram.** Foto até 8 MB; vídeo, áudio e PDF até 25 MB. Acima disso, recusa na hora.
- **Áudio gravado no Safari** já é mp4 e vai direto; o do Firefox (ogg) e o do Chrome (webm) são convertidos para m4a.
- **Reação.** A reação da cliente aparece na conversa ("Reagiu com ❤") e não abre espera, como no WhatsApp.
- **Mensagens de grupo** não existem na API do Instagram: nada a tratar.
- **A conversa está com outro app** (roteamento da Meta). Se o Kommo for o app padrão da Página, as mensagens chegam
  para a Plataforma "em espera" (standby): são gravadas igual. O envio da Plataforma pode voltar recusado porque o
  controle da conversa é do Kommo; a mensagem fica "não entregue" com "A conversa está com outro app no Instagram
  (Kommo). Responda por ele até a virada.". A Plataforma nunca toma o controle sozinha.
- **A mesma pessoa no WhatsApp e no Instagram** são duas conversas, uma por canal. Juntar as duas na ficha é da Fase 3.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A Plataforma DEVE receber os avisos do Instagram num endereço próprio, verificar a assinatura com o
  segredo do app da Meta (o mesmo do WhatsApp) e responder o desafio de verificação. Assinatura errada ou canal
  desligado → recusa sem gravar.
- **FR-002**: Todo aviso válido DEVE ser gravado cru antes de qualquer processamento e reprocessado pela varredura da
  325 se falhar (mesma garantia: nada se perde num deploy).
- **FR-003**: Cada contato do Instagram DEVE virar uma conversa do canal Instagram, única por contato (o id do
  Instagram de quem escreveu), sem telefone. O nome e o @usuário vêm do perfil, buscado na criação e de novo se faltar
  (no máximo uma vez por dia).
- **FR-004**: As mensagens recebidas (texto, foto, vídeo, áudio, arquivo, story, publicação compartilhada, reels) DEVEM
  ser gravadas sem duplicar pelo id da mensagem; a mídia é baixada pelo link do anexo logo depois de gravar, com as
  retentativas da 325. Mensagem que chega "em espera" (a conversa está com outro app) é gravada do mesmo jeito.
- **FR-005**: A reação da cliente DEVE aparecer na conversa; a reação removida também. A mensagem apagada pela cliente
  DEVE trocar o texto por "Mensagem apagada pela cliente.".
- **FR-006**: O aviso de visto DEVE marcar como "lida" a mensagem enviada indicada (e as anteriores ainda não lidas da
  mesma conversa).
- **FR-007**: O eco (mensagem que saiu da conta da Manto por outro caminho) DEVE aparecer como enviada por outro app,
  encerrar a espera e não atribuir responsável. O eco de uma mensagem que a própria Plataforma enviou não duplica.
- **FR-008**: A equipe DEVE poder enviar pelo Instagram texto (até 1.000 caracteres), foto (png/jpeg/gif, até 8 MB),
  vídeo (até 25 MB), áudio (aac/m4a/wav/mp4, até 25 MB) e PDF (até 25 MB). Outro tipo ou tamanho → recusa na hora,
  apontando o campo.
- **FR-009**: O áudio gravado no navegador em webm ou ogg DEVE ser convertido para m4a antes de ir para o Instagram.
- **FR-010**: A janela do Instagram DEVE seguir a regra da Meta: até 24 h depois da última mensagem da cliente, envio
  normal; de 24 h a 7 dias, envio com a marca de resposta humana; depois de 7 dias, recusa com o texto do cenário 12.
- **FR-011**: O envio pelo Instagram DEVE seguir as garantias da 325: chave de envio contra clique duplo, mensagem
  gravada antes de chamar a Meta, falha vira "não entregue" com motivo legível, trava do ambiente local.
- **FR-012**: Responsável, espera, alerta de 15 min, notas internas e respostas rápidas (feature 328) DEVEM valer para
  as conversas do Instagram sem diferença.
- **FR-013**: A lista DEVE mostrar o ícone do canal em cada conversa e filtrar por canal ("Todos", "WhatsApp",
  "Instagram"); a conversa aberta mostra o @usuário no lugar do telefone e o ícone do canal no cabeçalho.
- **FR-014**: A caixa de envio do Instagram DEVE dizer em que janela está: nada de especial dentro de 24 h; "Fora das
  24 horas: a resposta vai como resposta da equipe, até 7 dias depois da última mensagem da cliente." de 24 h a 7
  dias; e, depois de 7 dias, o aviso sem campo de envio. "Enviar modelo" não aparece no Instagram.
- **FR-015**: Sem as chaves do Instagram, o canal DEVE ficar desligado: o endereço do aviso responde 404, o envio é
  recusado com "O Instagram ainda não foi configurado.", e o filtro "Canal" não aparece.
- **FR-016**: Todos os endpoints, novos e alterados, seguem o RBAC da 325 (COMERCIAL e SUPERADMIN, papel real).
- **FR-017**: Os textos novos seguem o Princípio XV.

### Entidades

Modelo em `app/models.py`, migration à mão.

- **Conversa** (coluna nova): `usuario` (o @usuário do Instagram, sem a arroba; vazio no WhatsApp) e o carimbo de
  quando o perfil foi buscado pela última vez, para a regra de "no máximo uma vez por dia". O canal (`instagram`) e o
  contato (id do Instagram) já existem desde a 325.
- **Mensagem**, **mídia** e **aviso cru**: as tabelas da 325, sem mudança de estrutura.

### RBAC

- `GET|POST /api/webhooks/instagram`: público, só com a assinatura (POST) ou o token de verificação (GET) certos;
  desligado → 404.
- `GET /api/conversas` ganha o filtro `canal`; `POST /api/conversas/<id>/mensagens` passa a enviar pelo canal da
  conversa. Mesmo gate da 325 (`pode_conversas`).

## Verificação (`verify_330.py`) *(obrigatório — Princípio VIII)*

Arquivo `specs/330-crm-instagram-direct/verify_330.py`, contra o `manto_local`, no molde do `verify_328`: disjuntor de
rede, dublê da Meta (envio, upload, perfil e download), conferência por conexão separada, login só pela API e
limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Desafio de verificação certo e errado | 200 com o desafio; 404 | errado **sim** |
| 2 | Texto do Instagram | conversa `instagram`, nome e @usuário do perfil, espera aberta | não |
| 3 | Mesmo aviso reenviado | uma mensagem só | não |
| 4 | Assinatura errada ou ausente | 404, nada gravado | **sim** |
| 5 | Foto recebida | baixada pelo link, guardada, servida pela rota da 325 | não |
| 6 | Story, reels, efêmera e não suportada | textos dos casos de borda | não |
| 7 | Cliente apaga a mensagem | "Mensagem apagada pela cliente." | não |
| 8 | Reação e reação removida | aparecem; não abrem espera | não |
| 9 | Perfil indisponível | "Contato do Instagram"; nova busca só depois de um dia | não |
| 10 | Ana responde com a janela aberta | corpo certo na Meta (id da cliente, texto), Ana responsável, espera encerrada | não |
| 11 | Resposta entre 24 h e 7 dias | vai com a marca de resposta humana | não |
| 12 | Resposta depois de 7 dias | 409 com o texto da janela | **sim** |
| 13 | Foto enviada | upload para a Meta como imagem; cópia local guardada | não |
| 14 | Áudio webm gravado | sai como m4a para o Instagram | não |
| 15 | Planilha ou foto acima de 8 MB | 422 no arquivo | **sim** |
| 16 | Visto da cliente | a enviada fica lida | não |
| 17 | Meta recusa a marca de resposta humana | "não entregue" com o motivo legível | não |
| 17b | Meta recusa porque a conversa está com outro app | "não entregue" com o motivo do roteamento | não |
| 18 | Eco de outro app | enviada por outro app, espera encerrada, sem responsável | não |
| 18b | Mensagem "em espera" (standby) | gravada como a recebida comum | não |
| 19 | Eco da própria mensagem | não duplica | não |
| 20 | Canal desligado | webhook 404; envio recusado; filtro ausente | **sim** |
| 21 | Casting na lista e no envio do Instagram | 403 | **sim** |
| 22 | Filtro por canal | só Instagram / só WhatsApp | não |
| 23 | Limpeza | conversas, avisos, mídias e usuários de teste apagados | — |

Conferência de tela: lista com ícones e filtro "Canal", conversa do Instagram (@usuário, aviso de janela, sem "Enviar
modelo"), em desktop e em 375×812.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Toda mensagem do Direct que a Meta entrega aparece na caixa em até 10 segundos, sem duplicar.
- **SC-002**: A equipe responde o Direct sem abrir o Kommo nem o app do Instagram em 100% dos casos dentro de 7 dias.
- **SC-003**: Nenhuma mensagem é enviada sozinha pela Plataforma durante o piloto (zero respostas automáticas).
- **SC-004**: Um áudio gravado em qualquer dos três navegadores chega tocável no Instagram da cliente.

## Fora de escopo

- Comentários dos posts (decisão do dono).
- Respostas automáticas, bot e mensagens fora da janela além da marca de resposta humana.
- Ligação da conversa do Instagram à ficha do cliente e atribuição do anúncio de origem (Fase 3; o dado bruto do
  anúncio já fica guardado na mensagem).
- Notificação no celular (2c).
- Troca do app principal no roteamento da Meta (é operação da virada, Fase 4, feita pelo dono no painel).

## Docs a atualizar

- `docs/01`: coluna nova, webhook e envio do Instagram, variáveis, RBAC §4.3.
- `docs/02`: a tela Conversas com o canal Instagram.
- `docs/03`: entrada no topo.
- `docs/04`: invariantes do Instagram na linha "Conversas".
- `docs/05`: a configuração desligada e o que ficar de dívida.
- `docs/PLANO_CRM_PROPRIO.md`: Fase 2b marcada; a decisão de ligação pela Página registrada no lugar do "Instagram
  Login" do plano.

## Premissas

- **Mesmo app da Meta** do WhatsApp, com o produto de mensageria do Instagram: o segredo do app e o token de
  verificação do aviso são os mesmos. O token de acesso do Instagram é o da Página (ou de um usuário do sistema do
  portfólio com a Página atribuída), em variável própria.
- **O Instagram da Manto está ligado a uma Página do Facebook da Manto** e com "Permitir acesso às mensagens" ligado
  nas configurações de mensagens. Se não estiver, o dono liga antes do teste (quickstart).
- **No piloto, o roteamento da Meta fica no padrão**: todos os apps conectados recebem os avisos. A Plataforma só envia
  quando alguém da equipe manda; responder pelo Kommo e pela Plataforma na mesma conversa é possível e não é proibido.
- **A marca de resposta humana** depende de permissão própria no App Review. Até ela sair, o envio de 24 h a 7 dias
  pode voltar recusado (caso de borda).
- **Piloto com o Instagram de verdade, em modo de desenvolvimento.** Não existe "número de teste" do Instagram como no
  WhatsApp: a ligação é com o Instagram da Manto. Enquanto o app da Meta está em desenvolvimento (antes do App Review),
  só chegam os avisos de quem tem papel no app — a equipe testa mandando Direct pelas contas pessoais e as clientes
  continuam só no Kommo. A confirmar no primeiro teste (quickstart).
- **Volume**: o mesmo da caixa do WhatsApp (dezenas de conversas por dia); a varredura e o alerta da 325/328 servem.
