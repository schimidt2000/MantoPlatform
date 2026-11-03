# Feature 332 — Avisos das Conversas no celular

**Branch**: `332-crm-avisos-no-celular` (da `330-crm-instagram-direct`, fora da `main`: o dono adiou a publicação) ·
**Created**: 2026-11-03 · **Status**: Rascunho · **Migration**: sim, aditiva (1 tabela nova) · **Nível**: 1 (feature)

**Input**: pedido do dono (03/11): "Começar a 2c". É a Fase 2c do `docs/PLANO_CRM_PROPRIO.md`, o aviso no celular,
com as decisões do mesmo dia (Clarifications).

## O pedido, nas palavras do dono *(obrigatório)*

> "Pelo kommo ser ruim de mexer e usar no celular, só uma pessoa sabe mexer. Se tornarmos a nossa usabilidade boa o
> suficiente, a ideia é que 3 pessoas usem." (30/10)

> "Começar a 2c" (03/11)

O plano diz, na Fase 2: "Sino e push no celular (PWA)". Sem o aviso no celular, quem não está com a Plataforma aberta
só fica sabendo da cliente pelo app do WhatsApp/Instagram — e o Kommo continua sendo necessário.

## Clarifications

### Session 2026-11-03

- Q: O que deve tocar no celular de quem ativar os avisos? → A: **Os avisos das Conversas e cada mensagem nova da
  cliente.**
  - Avisos das Conversas: cliente esperando há 15 min e conversa transferida para você.
  - A mensagem nova vai para o responsável; sem responsável, para a equipe do Comercial.
- Q: Em que horário os avisos tocam? → A: **A qualquer hora.** Cada pessoa silencia no próprio celular ou desativa na
  Plataforma. O alerta de 15 min continua só das 9h às 21h (regra da 328).

## Cenários e Verificação *(obrigatório)*

### História 1 — Ativar os avisos neste aparelho (Prioridade: P1)

Na tela de Conversas, o botão "Avisos no celular" abre um painel com a situação deste aparelho e o botão "Ativar
avisos". O navegador pede a permissão; aceita, o aparelho fica registrado para a pessoa logada. Dá para desativar no
mesmo lugar. Cada aparelho (celular, computador) é ativado à parte.

**Por que esta prioridade**: sem o registro do aparelho, nada toca.

**Verificação**: cenários 1 a 5 do `verify_332.py`.

**Cenários de aceite**:

1. **Dado** a Ana logada, **Quando** ela ativa os avisos, **Então** o aparelho fica registrado para ela.
2. **Dado** o mesmo aparelho ativado de novo (ou por outra pessoa no mesmo navegador), **Quando** registra, **Então**
   continua um registro só, agora da pessoa logada.
3. **Dado** um aparelho ativado, **Quando** a pessoa desativa, **Então** o registro some e nada mais toca nele.
4. **Dado** um iPhone fora da Tela de Início, **Quando** a pessoa abre o painel, **Então** ele explica: "No iPhone,
   adicione a Plataforma à Tela de Início (Compartilhar → Adicionar à Tela de Início) e abra por lá para ativar."
5. **Dado** alguém do Casting, **Quando** tenta registrar, **Então** recebe 403.

### História 2 — O celular toca quando a cliente escreve (Prioridade: P1)

Quando chega mensagem nova da cliente (WhatsApp ou Instagram), o celular do responsável toca com o nome do contato e o
trecho da mensagem; sem responsável, tocam os aparelhos da equipe. Tocar no aviso abre a conversa. Várias mensagens
seguidas da mesma conversa substituem o aviso anterior, em vez de empilhar.

**Por que esta prioridade**: é o que deixa a equipe largar o app do Kommo.

**Verificação**: cenários 6 a 10.

**Cenários de aceite**:

1. **Dado** uma conversa sem responsável, **Quando** a cliente escreve, **Então** os aparelhos de toda a equipe tocam
   com "{Nome}" e o trecho, e o link da conversa.
2. **Dado** uma conversa da Ana, **Quando** a cliente escreve, **Então** só os aparelhos da Ana tocam.
3. **Dado** um eco do celular, uma reação ou um reenvio do mesmo aviso, **Quando** chegam, **Então** nada toca.
4. **Dado** um aparelho que o serviço de avisos diz que não existe mais, **Quando** a Plataforma tenta avisar,
   **Então** o registro é apagado.

### História 3 — Os avisos das Conversas também tocam (Prioridade: P2)

O alerta de cliente esperando há 15 minutos e a conversa transferida para você, que já aparecem no sino (328), também
tocam no celular de quem os recebe.

**Verificação**: cenários 11 e 12.

### Casos de borda

- **Ambiente local**: nada sai para o serviço de avisos (trava, como no e-mail e no WhatsApp).
- **Chaves não configuradas**: o painel diz "Os avisos no celular ainda não foram configurados." e o botão não aparece.
- **Permissão negada**: "O navegador bloqueou os avisos. Libere nas configurações do navegador e tente de novo." — o
  pedido não reaparece sozinho.
- **Navegador sem suporte**: "Este navegador não recebe avisos." (por exemplo, iPhone com iOS anterior ao 16.4).
- **Pessoa que perdeu o papel ou foi desativada**: os aparelhos dela não tocam mais (filtro no envio).
- **Falha do serviço de avisos** (fora do ar): o aviso se perde para aquele aparelho; o sino e a lista continuam
  valendo. Não há reenvio.
- **Mensagem com mídia sem texto**: o corpo é o rótulo da prévia ("Foto", "Áudio").

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A Plataforma DEVE ser instalável no celular (manifesto com nome, ícone e cores; abre em tela cheia) e
  ter um service worker que recebe e mostra o aviso e abre a conversa ao tocar.
- **FR-002**: Quem tem acesso às Conversas (COMERCIAL e SUPERADMIN, papel real) DEVE poder ativar e desativar os avisos
  em cada aparelho. O registro é único por aparelho (o endereço do serviço de avisos) e fica da pessoa logada.
- **FR-003**: Mensagem nova da cliente (WhatsApp ou Instagram, inclusive toque em botão) DEVE tocar nos aparelhos do
  responsável da equipe; sem responsável (ou com responsável sem acesso), nos da equipe. Eco, reação e reenvio não
  tocam.
- **FR-004**: O aviso da mensagem traz o nome do contato como título, o trecho da última mensagem como corpo e o link
  `/conversas?c={id}`; avisos da mesma conversa se substituem.
- **FR-005**: Os avisos `conversa.esperando` e `conversa.transferida` DEVEM tocar nos aparelhos de quem os recebe no
  sino, com o mesmo título e link.
- **FR-006**: O envio do aviso DEVE ser feito depois de gravar o fato (nunca dentro da transação) e não pode atrasar
  nem derrubar o processamento: falha só é registrada no log.
- **FR-007**: Aparelho que o serviço de avisos declara inexistente (404/410) DEVE ter o registro apagado.
- **FR-008**: O envio DEVE ficar travado no ambiente local (escape explícito para o teste).
- **FR-009**: Sem as chaves do serviço de avisos, o recurso fica desligado: a API diz `ligado: false` e o registro é
  recusado.
- **FR-010**: Os textos novos seguem o Princípio XV.

### Entidades

- **Aparelho com aviso** (`push_assinaturas`): pessoa, endereço do serviço (único), as duas chaves do aparelho, o
  navegador e os horários (criado, último aviso).

### RBAC

- `GET /api/push/chave`, `POST /api/push/aparelhos`, `DELETE /api/push/aparelhos`: COMERCIAL e SUPERADMIN
  (`pode_conversas`), papel real.

## Verificação (`verify_332.py`) *(obrigatório — Princípio VIII)*

Contra o `manto_local`, com disjuntor de rede e dublê do envio de aviso. Login pela API e limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 0 | Cifra contra o vetor oficial do RFC 8291 | o corpo cifrado bate byte a byte | não |
| 1 | Chave pública | `ligado` e a chave | não |
| 2 | Ana registra o aparelho | gravado para a Ana | não |
| 3 | O mesmo aparelho registrado pela Bia | um registro só, agora da Bia | não |
| 4 | Ana desativa | registro apagado | não |
| 5 | Casting registra; registro sem chaves | 403; 422 | **sim** |
| 6 | Mensagem nova do WhatsApp sem responsável | aviso para Ana e Bia, título, corpo e link | não |
| 7 | Mensagem nova numa conversa da Ana | aviso só para a Ana | não |
| 8 | Eco, reação e reenvio | nenhum aviso | não |
| 9 | Mensagem do Instagram | aviso com o nome do perfil | não |
| 10 | Serviço responde 410 | registro apagado | não |
| 11 | Alerta de 15 min | aviso para quem recebeu no sino | não |
| 12 | Transferência para a Bia | aviso para a Bia | não |
| 13 | Ambiente travado | nada sai | **sim** |
| 14 | Sem chaves | `ligado: false`; registro 503 | **sim** |
| 15 | Limpeza | registros e usuários de teste apagados | — |

Conferência de tela: o painel "Avisos no celular" em desktop e 375×812 (no Browser pane a permissão pode ser negada:
conferir o texto), o manifesto e o service worker servidos.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: A mensagem nova da cliente toca no celular do responsável em até 10 segundos do aviso da Meta.
- **SC-002**: A equipe ativa os avisos em até 3 toques a partir da tela de Conversas.
- **SC-003**: Nenhum aviso toca para eco, reação ou reenvio (zero avisos falsos).

## Fora de escopo

- Avisos de outras áreas do sino (formulário, PIX, cancelamento…): o dono escolheu só as Conversas.
- Horário de silêncio na Plataforma (fica com o celular).
- Contagem no ícone do app (badge) e ações no próprio aviso (responder sem abrir).
- Reenvio de aviso que falhou.

## Docs a atualizar

- `docs/01`: tabela, endpoints, RBAC, variáveis e a cifra própria (provada pelo vetor do RFC 8291).
- `docs/02`: o painel na tela Conversas; o app instalável.
- `docs/03`: entrada no topo.
- `docs/04`: invariantes do aviso no celular na linha "Conversas".
- `docs/05`: o recurso desligado até as chaves.
- `docs/PLANO_CRM_PROPRIO.md`: Fase 2c.

## Premissas

- **Web Push padrão** (o mesmo que Chrome, Edge, Firefox e Safari usam): chaves VAPID da Plataforma, sem conta em
  serviço de terceiros. No iPhone, só com a Plataforma instalada na Tela de Início (iOS 16.4+).
- **Ícone**: o que a casa já usa no Jinja (`app/static/apple-touch-icon-app.png`, o "M" branco sobre o roxo),
  redimensionado para o manifesto.
- **Volume**: dezenas de mensagens por dia; o envio direto, logo depois do processamento do aviso, basta.
