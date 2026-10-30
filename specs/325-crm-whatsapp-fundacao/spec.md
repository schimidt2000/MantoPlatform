# Feature 325 — Conversas: o WhatsApp da Manto dentro da Plataforma (fundação do CRM próprio)

**Branch**: `325-crm-whatsapp-fundacao` (da `main`) · **Created**: 2026-10-30 · **Status**: Rascunho ·
**Migration**: sim, aditiva (tabelas novas, nenhuma coluna alterada) · **Nível**: 1 (feature) —
constituição, Princípio VI

**Input**: pedido do dono: "CRM próprio — Fase 1: fundação do WhatsApp na Plataforma (substituir o
Kommo, plano em docs/PLANO_CRM_PROPRIO.md)…" (texto completo no topo da conversa de 30/10/2026;
resumo abaixo).

## O pedido, nas palavras do dono *(obrigatório)*

> "Definitivamente sinto que chegou o momento de eu avançar com a ideia de termos um CRM próprio.
> […] Muitas das coisas poderiam ser automatizadas, principalmente de marketing e comercial. E eu
> não gosto do aplicativo do Kommo, acho ele muito feio, muito ruim de mexer."

> "O que é usado basicamente é a conversa. Talvez seria mais interessante usar apenas o WhatsApp
> Web, mas o problema é que quero evoluir e ver clientes que chegam por campanhas e por aí vai."

> "Se tornarmos a nossa usabilidade boa o suficiente, a ideia é que 3 pessoas usem sempre pelo
> mesmo número."

O panorama aprovado (`docs/PLANO_CRM_PROPRIO.md`) divide o CRM em seis fases. **Esta é a Fase 1**:
a Plataforma passa a receber e enviar WhatsApp pela API oficial da Meta, com uma tela mínima de
conversas. Ela é testada no **número de teste grátis da Meta**. O número principal (+55 11
97057-0577, hoje em coexistência com o app WhatsApp Business e com o Kommo) **não é tocado** nesta
fase.

## Clarifications

### Session 2026-10-30

Resolvidas pelo agente, pela autonomia que o dono deu em 30/10 ("me chame apenas em decisões
importantes"), seguindo o plano aprovado. Nenhuma muda escopo nem dinheiro.

- Q: A contagem de "não lidas" é da equipe (compartilhada) ou de cada pessoa? → A: Compartilhada por
  conversa: um número, uma caixa, como no WhatsApp Web. A conversa deixa de contar como não lida
  quando qualquer pessoa da equipe a abre.
- Q: Abrir a conversa na Plataforma deve mostrar à cliente que a mensagem foi lida (tique azul)?
  → A: Sim. Ao abrir, a última mensagem recebida é marcada como lida também na Meta, com a mesma trava
  de ambiente local do envio (FR-016).

## Cenários e Verificação *(obrigatório)*

### História 1 — A mensagem da cliente chega à Plataforma (Prioridade: P1)

A cliente escreve no WhatsApp da Manto. Em poucos segundos, a conversa aparece na tela **Conversas**
do app interno, com o nome e o telefone dela. Quem já tem ficha na base de clientes aparece ligada à
ficha, e a mensagem fica guardada para sempre, sem depender do Kommo.

**Por que esta prioridade**: sem receber, não há CRM. É também a peça que dá autonomia sobre o
histórico: hoje o Kommo só exporta os leads, não as conversas.

**Verificação**: cenários 1 a 6 do `verify_325.py`. Eles mandam ao webhook avisos no formato da Meta,
assinados com o segredo de teste, e conferem por conexão separada a conversa, a mensagem, o vínculo
com o cliente e a idempotência.

**Cenários de aceite**:

1. **Dado** o WhatsApp configurado, **Quando** chega uma mensagem de texto de um telefone novo,
   **Então** nasce uma conversa com o nome de perfil do WhatsApp e a mensagem fica gravada como
   recebida.
2. **Dado** um cliente com aquele telefone na base de clientes, **Quando** chega a mensagem, **Então**
   a conversa fica ligada à ficha dele, inclusive quando o WhatsApp manda o número brasileiro sem o
   nono dígito.
3. **Dado** que a Meta reenvia o mesmo aviso (o que ela faz quando a resposta demora ou falha),
   **Quando** o aviso chega de novo, **Então** nenhuma mensagem é duplicada.
4. **Dado** um aviso sem assinatura válida, **Quando** ele chega, **Então** é recusado e nada é
   gravado.

---

### História 2 — Responder pela Plataforma e ver se chegou (Prioridade: P1)

A vendedora abre a conversa, digita e envia. A mensagem aparece na hora, com a situação "enviada",
que depois vira "entregue" e "lida". Se a Meta recusar, aparece "não entregue", com o motivo em
português e o que fazer. A conversa mostra **quem** da equipe enviou cada mensagem.

**Por que esta prioridade**: responder é o trabalho do dia a dia. Sem isso, a tela é só um espelho.

**Verificação**: cenários 7 a 10. Eles usam o envio com o cliente da Meta substituído por um dublê no
verify: nada sai para a Meta de verdade. Conferem a mensagem gravada com o autor, a situação vinda
dos avisos de status e a recusa fora da janela.

**Cenários de aceite**:

1. **Dado** uma conversa com mensagem da cliente nas últimas 24h, **Quando** a vendedora envia um
   texto, **Então** a mensagem é gravada como enviada por ela, com a situação "enviada".
2. **Dado** uma mensagem enviada, **Quando** chegam os avisos de entregue e de lida, **Então** a
   situação avança, e um aviso atrasado nunca faz a situação voltar.
3. **Dado** que a última mensagem da cliente tem mais de 24h, **Quando** a vendedora tenta enviar
   texto livre, **Então** o sistema recusa, explica a regra da janela e oferece os modelos aprovados.
4. **Dado** que a Meta devolve falha num envio, **Quando** chega o aviso de falha, **Então** a
   mensagem fica "não entregue", com o motivo legível.

---

### História 3 — Foto, áudio, vídeo e documento (Prioridade: P2)

A cliente manda foto do salão, áudio ou o comprovante em PDF. A Plataforma guarda o arquivo na hora,
porque o link da Meta expira. Na conversa, a foto aparece, o áudio toca e o documento abre. A
vendedora também envia foto, documento (como o PDF do orçamento) e áudio a partir de um arquivo.

**Por que esta prioridade**: na venda de festa, áudio e foto são metade da conversa. Sem mídia, a
equipe voltaria ao celular.

**Verificação**: cenários 11 a 13. O download da Meta é substituído por um dublê que devolve bytes
conhecidos. O verify confere o arquivo gravado no storage, o acesso dele restrito a quem tem o papel
e o envio de mídia.

**Cenários de aceite**:

1. **Dado** uma mensagem recebida com imagem, áudio, vídeo ou documento, **Quando** ela é processada,
   **Então** o arquivo é baixado e guardado na Plataforma, e a conversa o exibe.
2. **Dado** que o download falha (Meta fora do ar, link vencido), **Quando** a mensagem é processada,
   **Então** ela é gravada mesmo assim, com a mídia marcada como pendente, e uma nova tentativa
   acontece depois.
3. **Dado** uma conversa aberta na janela de 24h, **Quando** a vendedora escolhe um arquivo e envia,
   **Então** a mídia sai e fica gravada na conversa como enviada por ela.

---

### História 4 — Falar com quem sumiu: modelos aprovados (Prioridade: P2)

Passadas 24h desde a última mensagem da cliente, o WhatsApp só aceita **modelos** (templates)
aprovados pela Meta. A vendedora vê a lista de modelos aprovados, preenche as variáveis (por exemplo,
o nome da cliente) e envia. Os modelos são criados e aprovados no gerenciador da Meta, não na
Plataforma.

**Por que esta prioridade**: o follow-up de orçamento, a maior oportunidade apontada no plano, depende
disso. Nesta fase, o envio é manual.

**Verificação**: cenários 14 e 15. A lista de modelos e o envio passam por um dublê da Meta. O verify
confere que só modelos aprovados aparecem e que o envio grava a mensagem com o texto final, já com as
variáveis.

**Cenários de aceite**:

1. **Dado** modelos aprovados na conta, **Quando** a vendedora abre "Enviar modelo", **Então** vê só os
   aprovados, com o texto e os campos de variável.
2. **Dado** um modelo com variável, **Quando** ela preenche e envia, **Então** a mensagem é gravada com
   o texto já preenchido e o nome do modelo.

---

### História 5 — Desligado por padrão e travado fora da produção (Prioridade: P1)

Sem configuração, o módulo não existe para o mundo: o endereço do webhook responde "não encontrado"
e nenhum envio acontece. Na máquina de desenvolvimento (banco local, espelho da produção), nada é
enviado à Meta, a não ser com uma liberação explícita para testes.

**Por que esta prioridade**: é a regra da casa para integração externa (constituição, Princípio XIV).
O `manto_local` traz dados reais, e um envio acidental falaria com cliente de verdade.

**Verificação**: cenários 16 a 18. Configuração vazia faz o webhook devolver 404 e o envio ser
recusado. Banco local sem liberação faz o envio não chamar a Meta. Papel sem permissão (Casting) leva
403 na lista e no envio: **deve falhar**.

**Cenários de aceite**:

1. **Dado** o token vazio, **Quando** alguém chama o webhook, **Então** a resposta é 404.
2. **Dado** o banco local sem a liberação de teste, **Quando** alguém envia uma mensagem, **Então**
   nada sai para a Meta e a tela explica que o envio está travado neste ambiente.
3. **Dado** um usuário só com o papel Casting, **Quando** ele abre Conversas ou tenta enviar,
   **Então** recebe 403, e o menu não mostra o item.

---

### História 6 — Mensagens enviadas pelo app do celular (coexistência) (Prioridade: P3)

Quando o número estiver em coexistência (Fase 4), o que a equipe responde pelo app WhatsApp Business
no celular também aparece na conversa da Plataforma, marcado como "enviada pelo celular".

**Por que esta prioridade**: o número de teste desta fase não tem coexistência. A estrutura, porém,
precisa nascer preparada, para que a virada não exija migration nova.

**Verificação**: cenário 19. Um aviso de eco no formato documentado pela Meta grava a mensagem como
enviada, sem autor da equipe e com a origem "celular".

**Cenários de aceite**:

1. **Dado** um aviso de eco de mensagem enviada pelo app, **Quando** ele chega, **Então** a mensagem é
   gravada como enviada pelo celular, sem duplicar se o aviso se repetir.

---

### Casos de borda

- **Nono dígito.** O WhatsApp pode identificar um celular brasileiro sem o nono dígito (por exemplo,
  `55 11 7057-0577` em vez de `55 11 97057-0577`). O vínculo com a ficha procura as duas formas, e a
  conversa guarda o identificador exato que a Meta usa, porque é para ele que a resposta vai.
- **Status antes da mensagem.** Um aviso de status pode chegar para uma mensagem que ainda não foi
  gravada (corrida entre o envio e o aviso). O aviso não se perde: é aplicado quando a mensagem
  existir, ou fica registrado como pendente.
- **Tipos que a Plataforma não exibe nesta fase** (figurinha, localização, contato, reação, enquete,
  mensagem interativa, apagada). Ficam gravados com o tipo e um texto curto, por exemplo
  "Localização enviada — abra no celular para ver.". Nunca derrubam o processamento.
- **Mensagem de grupo ou de número não aceito pela Meta.** É registrada no aviso cru e ignorada sem
  erro.
- **Duas pessoas respondendo ao mesmo tempo.** As duas mensagens saem. Cada uma mostra o autor.
  Não há trava de conversa nesta fase.
- **Plataforma fora do ar durante um deploy.** A Meta reenvia os avisos que falharam. O que chega é
  gravado cru antes de qualquer processamento, e o processamento que morrer no meio é refeito por
  uma varredura.
- **Arquivo grande.** O limite do WhatsApp chega a 100 MB por documento. Ver Premissas.
- **Telefone com ficha duplicada.** Não deveria existir (`Client.phone` é único), mas o vínculo pega
  a ficha exata do telefone normalizado e nunca escolhe "a primeira" de várias.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE oferecer um endpoint público de webhook que responda ao desafio de
  verificação da Meta quando o token de verificação confere, e devolva 404 quando o módulo não está
  configurado.
- **FR-002**: O sistema DEVE recusar todo aviso recebido sem a assinatura válida do segredo do app
  Meta, e nada gravar nesse caso.
- **FR-003**: O sistema DEVE gravar cada aviso recebido, cru, antes de processá-lo, e responder à
  Meta rapidamente. Avisos cujo processamento falhou DEVEM ser reprocessados depois, sem intervenção.
- **FR-004**: O sistema DEVE criar ou reaproveitar a conversa pelo par (canal, identificador do
  contato no canal), com o canal "whatsapp" nesta fase. A estrutura DEVE aceitar "instagram" na
  Fase 2 sem migration.
- **FR-005**: O sistema DEVE ligar a conversa à ficha do cliente cujo telefone normalizado
  corresponda ao do contato, nas formas com e sem o nono dígito brasileiro. Se não houver ficha, a
  conversa fica sem vínculo. A tentativa se repete a cada mensagem enquanto a conversa estiver sem
  vínculo.
- **FR-006**: O sistema DEVE gravar cada mensagem com: direção (recebida ou enviada), tipo, texto ou
  legenda, identificador da Meta (único, para não duplicar), horário, autor da equipe (quando enviada
  pela Plataforma) e origem (contato, para a recebida; Plataforma, celular ou outro provedor, para a
  enviada).
- **FR-007**: O sistema DEVE baixar a mídia recebida (imagem, áudio, vídeo, documento, figurinha)
  para o storage da Plataforma no processamento do aviso, guardar tipo, tamanho e nome original, e
  marcar a mídia como pendente quando o download falhar, com nova tentativa posterior.
- **FR-008**: O arquivo de mídia de conversa DEVE ser servido só a quem tem acesso às conversas. Os
  demais recebem **404**.
- **FR-009**: O sistema DEVE atualizar a situação das mensagens enviadas a partir dos avisos de status
  (enviada → entregue → lida; ou não entregue, com o código e o motivo). A situação nunca regride.
- **FR-010**: Comercial e Superadmin DEVEM poder enviar texto livre numa conversa cuja última
  mensagem recebida tem menos de 24h. O sistema DEVE recusar o texto livre fora dessa janela, com
  mensagem que explica a regra.
- **FR-011**: Comercial e Superadmin DEVEM poder enviar imagem, documento, áudio e vídeo a partir de
  um arquivo, dentro da janela de 24h.
- **FR-012**: O sistema DEVE listar os modelos aprovados da conta (lidos da Meta) e permitir o envio
  de um modelo com as variáveis preenchidas, dentro ou fora da janela. A mensagem fica gravada com o
  texto final.
  - Nesta fase só aparecem os modelos cujas variáveis estão todas no **corpo**.
  - Ficam de fora (`docs/05` 182; convergência de 30/10): modelo com cabeçalho de
    imagem/vídeo/documento/localização, com variável no cabeçalho ou com botão de URL variável.
- **FR-013**: A tela **Conversas** DEVE mostrar a lista ordenada pela última mensagem, com nome,
  telefone, trecho da última mensagem, horário e quantidade de mensagens não lidas. A lista DEVE se
  atualizar sozinha em poucos segundos e permitir busca por nome ou telefone.
- **FR-014**: A conversa aberta DEVE mostrar as mensagens em ordem, com a situação das enviadas, o
  autor, a mídia exibível, o aviso de "janela fechada" quando for o caso e o link para a ficha do
  cliente quando houver vínculo. Ao abrir, as mensagens recebidas são marcadas como lidas na
  Plataforma (contagem compartilhada pela equipe) e a última recebida é marcada como lida na Meta
  (tique azul para a cliente), com a trava do FR-016.
- **FR-015**: Sem a configuração mínima (token de acesso, identificador do número, segredo do app e
  token de verificação), o webhook DEVE responder 404, e o envio DEVE ser recusado com mensagem clara.
  Sem configuração não existe item de menu.
- **FR-016**: Com o banco apontando para máquina local, o envio NÃO DEVE chamar a Meta, salvo com a
  liberação explícita de teste (constituição, Princípio XIV). A recusa é explicada na tela.
- **FR-017**: O sistema DEVE gravar como mensagem enviada, de origem "celular", os ecos de mensagens
  enviadas pelo app WhatsApp Business, quando o número estiver em coexistência.
- **FR-018**: Todo envio DEVE ser protegido contra duplicidade por clique duplo: o mesmo pedido de
  envio, repetido, não manda a mensagem duas vezes.
- **FR-019**: A tela DEVE ter estados próprios para:
  - carregando (esqueleto);
  - lista vazia ("Nenhuma conversa encontrada.");
  - módulo desligado (explica que falta a configuração);
  - erro de leitura ("Não foi possível carregar as conversas. Tente novamente.", com botão);
  - mídia ainda não guardada ("Arquivo sendo carregado…");
  - mídia que falhou ("Arquivo indisponível. Abra no celular.").
- **FR-020**: No celular (até 767 px de largura), a tela DEVE mostrar uma coluna de cada vez: a lista
  ou a conversa, com "Voltar" para a lista. A caixa de envio fica fixa no rodapé, e os alvos de toque
  da ação principal têm no mínimo 44 px. Nada deve exigir rolagem horizontal de 320 px a 430 px.
- **FR-021**: No computador, Enter DEVE enviar e Shift+Enter quebrar a linha. Com o envio em
  andamento, o botão mostra "Enviando…", fica desabilitado, e o texto digitado só sai do campo
  depois que a Plataforma confirma a gravação. Se der erro, o texto continua no campo.

### Entidades *(se houver dados)*

Modelo em `app/models.py`, migration à mão.

- **Conversa**: um contato num canal.
  - Atributos: canal (whatsapp, e instagram depois); identificador do contato no canal; nome de
    perfil; telefone normalizado; ficha de cliente (opcional); horário da última mensagem recebida
    (base da janela de 24h); horário e trecho da última mensagem; quantidade de não lidas.
  - Unicidade por (canal, identificador).
- **Mensagem**: uma mensagem de uma conversa.
  - Atributos: direção, tipo, texto, identificador da Meta (único), horário, situação, código e
    motivo de falha, autor da equipe, origem, nome do modelo usado e dados crus do aviso.
- **Mídia da mensagem**: o arquivo de uma mensagem.
  - Atributos: identificador da mídia na Meta, tipo, tamanho, nome original, caminho no storage,
    situação do download (pendente, guardada, falhou) e tentativas.
- **Aviso recebido (webhook)**: o corpo cru de cada aviso da Meta.
  - Atributos: assinatura conferida, situação do processamento, tentativas e erro. Serve à varredura
    de reprocessamento e à auditoria.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- Webhook `GET`/`POST` público. Sem login, autenticado pelo token de verificação (GET) e pela
  assinatura da Meta (POST). Sem configuração, responde 404.
- Leitura da lista, da conversa, dos modelos e do arquivo de mídia: **COMERCIAL, SUPERADMIN**.
  Mídia de quem não tem o papel responde 404.
- Envio de texto, mídia e modelo, e a marcação como lida: **COMERCIAL, SUPERADMIN**.
- Uma linha por endpoint na tabela de `docs/01` §4.3.

## Verificação (`verify_325.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/325-crm-whatsapp-fundacao/verify_325.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`. A Meta nunca é
chamada: o cliente HTTP da Meta é substituído por um dublê dentro do processo do verify, e a
configuração de teste (tokens falsos) é injetada no `app.config` do verify.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | GET de verificação com token certo | devolve o `hub.challenge` | não |
| 2 | POST de texto assinado, telefone novo | cria conversa e mensagem recebida, aviso cru gravado | não |
| 3 | POST do mesmo aviso de novo | nenhuma mensagem duplicada | não |
| 4 | POST de telefone de cliente existente sem o nono dígito | conversa ligada à ficha certa | não |
| 5 | POST com assinatura errada | 404, nada gravado | **sim** |
| 6 | Aviso cru com processamento quebrado → varredura | reprocessa e grava a mensagem | não |
| 7 | Envio de texto na janela (Comercial) | mensagem gravada, autor = usuário, situação "enviada" | não |
| 8 | Status entregue e lido (e um "enviada" atrasado) | situação avança e não regride | não |
| 9 | Envio de texto fora da janela | 409 `janela_fechada` com a explicação | **sim** |
| 10 | Status "falhou" com código | "não entregue" com motivo | não |
| 11 | Mídia recebida (dublê devolve bytes) | arquivo no storage, mídia "guardada" | não |
| 12 | Download falha → pendente → varredura | "pendente" e depois "guardada" | não |
| 13 | Arquivo de mídia por usuário Casting | 404 | **sim** |
| 14 | Lista de modelos (dublê) | só os aprovados | não |
| 15 | Envio de modelo com variável | mensagem gravada com texto final e nome do modelo | não |
| 16 | Configuração vazia | webhook 404, envio recusado | **sim** |
| 17 | Banco local sem liberação | envio não chama o dublê da Meta | **sim** |
| 18 | Casting lista ou envia | 403 | **sim** |
| 19 | Eco do app (coexistência) | gravada como enviada, origem "celular", sem duplicar | não |
| 20 | Clique duplo no envio (mesma chave) | uma mensagem só | não |
| 21 | Limpeza | conversas, mensagens, mídia, avisos e usuários descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela: Conversas (lista, conversa aberta, envio, modelo, mídia) no Browser pane, em
desktop e em viewport mobile 375×812, porque a equipe usa no celular.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Uma mensagem enviada ao número de teste aparece na tela Conversas em até 10 segundos.
- **SC-002**: Uma resposta digitada na Plataforma chega ao WhatsApp do destinatário e mostra "lida"
  na tela quando ele lê.
- **SC-003**: Zero mensagens duplicadas ou perdidas quando a Meta reenvia avisos ou quando a
  Plataforma reinicia no meio do processamento (conferido no verify e num deploy de teste).
- **SC-004**: 100% das mídias recebidas ficam guardadas na Plataforma e abrem na conversa, inclusive
  depois de o link da Meta expirar.
- **SC-005**: Com a configuração vazia, nenhum efeito externo e nenhuma tela nova aparecem para a
  equipe.
- **SC-006**: Uma pessoa do Comercial responde uma conversa pelo celular, na tela nova, sem precisar
  de explicação. É a régua "tão fácil quanto o WhatsApp Web", conferida pelo dono no piloto.

## Fora de escopo

- Instagram Direct (Fase 2). A tabela de conversa já nasce com o canal.
- Atribuição, transferência e "quem está atendendo"; notas internas; respostas rápidas; etiquetas
  (Fase 2).
- Push no celular e PWA (Fase 2). Nesta fase, atualização por consulta periódica e sino nenhum.
- Gravar áudio no navegador (Fase 2). Nesta fase, o áudio sai a partir de um arquivo.
- Criar a ficha do cliente a partir da conversa, ligar orçamento e formulário à conversa, funil
  derivado e canal de campanha pelo anúncio (Fase 3).
- Ligar o número principal, coexistência real, virar Tech Provider ou usar intermediário (Fase 4).
- IA de qualquer tipo (Fase 5) e automações ou bot (Fase 6).
- Criar ou editar modelos na Plataforma: eles são feitos no gerenciador da Meta.
- Importar o histórico do Kommo.

## Docs a atualizar

- `docs/01`: tabelas novas, endpoints, RBAC §4.3, variáveis de ambiente e trava §5.
- `docs/02`: tela Conversas.
- `docs/03`: entrada nova no topo.
- `docs/04`: domínio novo Conversas, com a janela de 24h, a idempotência e o nono dígito.
- `docs/05`: módulo desligado até o dono preencher as variáveis no Render.
- `docs/00` §3: domínio novo na tabela de domínios.
- `docs/PLANO_CRM_PROPRIO.md`: a Fase 1 marcada.

## Premissas

- **Quem usa**: Comercial e Superadmin, que já são os papéis de venda e de clientes. Financeiro fica
  de fora nesta fase.
- **Sem ficha automática**: contato desconhecido não vira ficha de cliente sozinho, porque talentos e
  fornecedores também escrevem para o número. Criar a ficha a partir da conversa é da Fase 3.
- **Guarda**: as conversas ficam guardadas sem prazo de exclusão nesta fase, como no Kommo hoje. A
  política de LGPD (prazo de guarda) entra antes da virada do número principal (Fase 4) e é
  registrada como dívida no `docs/05`.
- **Storage**: a mídia segue o storage atual (`save_file`, disco ou S3/R2), numa subpasta protegida
  por papel. Os limites de tamanho são os do WhatsApp; um teto de segurança fica no plano.
- **Tempo real**: a lista e a conversa aberta se atualizam por consulta periódica curta (sem
  websocket, que o proxy Node não passa hoje); o intervalo fica no plano.
- **A Meta, não a Plataforma, é dona dos modelos**: a lista é lida da Meta, com cache curto.
- **Configuração**: os segredos (token de acesso, segredo do app, token de verificação) só existem no
  painel do Render e no `.env` do dono. Os não secretos (versão da API, intervalo de consulta) têm
  default real em `app/config.py` (Princípio XIV).
- **Número de teste**: o dono cria o app na Meta (portfólio Manto Produções, já verificado) e obtém o
  número de teste grátis, que só fala com até 5 destinatários cadastrados. É suficiente para esta
  fase.
