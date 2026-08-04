# Research — Loja de Interações Virtuais (feature 205)

**Data**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

Fase 0 do `/speckit.plan`. Cada decisão abaixo foi verificada contra o código do repositório ou
contra a documentação pública do fornecedor — nada aqui é suposição não marcada.

---

## R1. InfinitePay — contrato real da integração

**Decisão**: usar `POST https://api.checkout.infinitepay.io/links` para criar o link por pedido e
`POST https://api.checkout.infinitepay.io/payment_check` como **fonte única de verdade** sobre
pagamento. O webhook é apenas um gatilho.

**O que a documentação pública descreve** ([Central de Ajuda InfinitePay](https://ajuda.infinitepay.io/pt-BR/articles/10766888-como-usar-o-checkout-da-infinitepay)):

| Item | Contrato |
|---|---|
| Criar link | `POST /links` com `handle`, `redirect_url`, `webhook_url`, `order_nsu`, `items[]`, `customer{}`, `address{}` |
| Resposta | `{"url": "https://checkout.infinitepay.com.br/<tag>?lenc=..."}` |
| Preços | **Em centavos, inteiros** — R$ 10,00 = `1000` |
| Retorno ao site | `redirect_url` recebe `receipt_url`, `order_nsu`, `slug`, `capture_method`, `transaction_nsu` |
| Webhook | `{invoice_slug, amount, paid_amount, installments, capture_method, transaction_nsu, order_nsu, receipt_url, items}`; responder `200` com `{"success": true}` — responder `400` faz a operadora **reenviar** |
| Reconsulta | `POST /payment_check` com `handle`, `order_nsu`, `transaction_nsu`, `slug` → `{success, paid, amount, paid_amount, installments, capture_method}` |

**Lacunas confirmadas na documentação pública** — e o que fazemos por causa delas:

1. **Não há assinatura de webhook.** A decisão do `/speckit.clarify` ("validar assinatura +
   reconsultar") era inexequível na metade da assinatura. Mantemos a intenção — *nunca confiar no
   aviso* — por três camadas: endereço de notificação com segredo no path
   (`/api/webhooks/infinitepay/<token>`, token em `SiteSetting`, revogável sem deploy);
   `payment_check` obrigatório antes de qualquer efetivação; e conferência de `paid_amount` contra
   o total congelado do pedido.
2. **Não há API de estorno documentada.** O sistema não pode devolver dinheiro sozinho. Registra a
   devolução, sinaliza e cobra até a conclusão; quem executa é uma pessoa no painel da operadora.
   **Mitigação real**: prevenir o conflito — antes de devolver um slot expirado ao estoque, rodar
   `payment_check`; se pago, efetivar em vez de liberar (FR-041a).
3. **Autenticação não documentada além do `handle`.** Tratado como configuração
   (`SiteSetting.infinitepay_handle` + eventual token), nunca hardcoded — Princípio III.

**`order_nsu` é a chave de idempotência.** É gerado por nós, único por pedido, e volta em todo
webhook e em toda reconsulta. É o que liga aviso → pedido sem depender de nada mais.

**Alternativas rejeitadas**: confiar no payload do webhook (sem assinatura, seria confiar em
entrada anônima da internet para liberar produto); criar o link no front (exporia o `handle` e
permitiria adulterar valor).

---

## R2. Sala de videochamada — Google Meet via Calendar API

**Decisão**: criar o evento no Google Calendar com `conferenceData.createRequest`
(`conferenceSolutionKey.type = "hangoutsMeet"`) e `conferenceDataVersion=1`, reusando
`app/calendar/service.py`. Nenhum fornecedor novo — atende a diretriz que proíbe Zoom/Twilio/Daily.

**Por que funciona no repositório atual**: `app/calendar/service.py:14` já usa o escopo
`https://www.googleapis.com/auth/calendar.events` (escrita inclusa) e `insert_event()` já cria
eventos ([service.py:217](app/calendar/service.py:217)). As credenciais são OAuth de usuário,
persistidas em `SiteSetting.google_token` e com refresh automático — não é conta de serviço.

**O que precisa mudar em `insert_event`**: aceitar `conference_request_id` opcional e passar
`conferenceDataVersion=1` no `insert`. Extensão da função existente, não uma segunda versão
(Princípio I).

**⚠️ Desvio consciente da diretriz do usuário — `google_html_link`**

A diretriz pede persistir o `google_html_link` e entregá-lo ao cliente. Isso está **errado** para o
fim pretendido, por dois motivos verificáveis no código:

- `CalendarEvent.google_html_link` já existe e já tem significado próprio: "link direto do evento no
  site do Google Calendar", capturado na sincronização ([models.py:215-218](app/models.py:215)).
  Reaproveitá-lo para outra coisa quebraria o botão "Editar no Google Agenda" (feature 117).
- Esse link **abre o Google Calendar e exige login com acesso ao calendário** — a mãe que comprou
  não tem. O que a família precisa é o link da sala: `hangoutLink` (ou
  `conferenceData.entryPoints[].uri` com `entryPointType == "video"`).

**Resolução**: persistimos os dois, em campos distintos. `google_html_link` continua o que sempre
foi (uso interno, preenchido pela sincronização); o link da sala vai em `VirtualOrder.meet_url`,
que é o único exposto à família. Nada da diretriz se perde — a fonte continua sendo a Calendar API.

**Risco operacional**: `createRequest` é assíncrono. A resposta pode vir com
`conferenceData.createRequest.status.statusCode == "pending"`, sem `hangoutLink`. Tratamento: um
`events.get` de reconciliação; se ainda pendente, a venda **permanece válida** e a pendência é
sinalizada à equipe (FR-037), com botão de "gerar sala novamente".

**Alternativas rejeitadas**: Meet standalone via Google Meet API (exige Workspace e escopo novo);
sala fixa por campanha (sobreposição entre famílias consecutivas).

---

## R3. Vídeo gravado — armazenamento da plataforma, servido sob validação

**Decisão (revista após o `/speckit.checklist`)**: o vídeo vai para `app/storage.py` e é servido
**exclusivamente** por um endpoint do Flask que valida o acesso a cada requisição. Nenhuma URL de
leitura direta é divulgada.

**Por que o Google Drive foi descartado**: o modelo de acesso que o Drive oferece para tocar o vídeo
sem login é `permissions().create(role="reader", type="anyone")` — "qualquer pessoa com o link".
Para um vídeo em que o nome da criança é dito em voz alta, isso transforma sigilo em "torcer para o
link não vazar" (CHK070). Some-se a isso a conta de serviço sem cota própria (exigiria Drive
compartilhado) e o escopo de escrita a reautorizar: o Drive custava mais e protegia menos.

**Atenção que a mudança não resolve sozinha**: `app/storage.py` devolve URL pública — em produção o
bucket R2/S3, no local `/uploads/<subfolder>/<uuid>`; `_save_to_object_storage` chega a aplicar
`ACL public-read` no AWS ([storage.py:166-169](app/storage.py:166)). Guardar ali **não** torna o
vídeo privado. Por isso FR-038e é explícito: o vídeo é servido por endpoint validado, e a URL direta
do armazenamento não é usada nem exposta. Duas formas de honrar isso, ambas compatíveis com o
`storage.py` atual (escolha na implementação):

1. o Flask lê o arquivo e devolve o stream, com `Range` para o player poder buscar; ou
2. o armazenamento gera URL assinada de curta duração, emitida só após a validação dupla.

O `subfolder` dos vídeos deve ficar **fora** de qualquer prefixo servido estaticamente, para o
arquivo não escapar pela porta dos fundos do servidor de arquivos.

**Consequência de custo**: o vídeo passa a consumir armazenamento e banda do serviço. Aceito — é o
preço de não expor dado de criança, e o volume é sazonal.

**Alternativas rejeitadas**: Vimeo (assinatura paga); Google Drive (privacidade, acima).

---

## R9. Sincronização não pode tocar em evento virtual

**Decisão**: os eventos criados pela venda nascem com `source='platform'` e
`event_type='VIRTUAL'`, e a rotina de sincronização os ignora na importação, na atualização e na
remoção.

**Por que é obrigatório**: a feature cria o evento na agenda externa (é de lá que sai a sala). A
sincronização existente lê aquele mesmo calendário. Sem exclusão explícita, ela reprocessaria o
evento e poderia sobrescrever título, horário ou vínculos de um evento **já pago** — e a remoção
manual do evento no Google chegaria a apagar o registro da venda em cascata. Foi a lacuna CHK062.

**Ponto de atenção na implementação**: a exclusão precisa valer em **todos** os caminhos da
sincronização, não só no de importação. Um caminho esquecido é indistinguível de não ter feito nada.
Edição externa detectada vira sinalização à equipe (FR-029b), nunca propagação.

---

## R4. Concorrência do soft lock e idempotência

**Decisão**: `SELECT ... FOR UPDATE` (`with_for_update()`) sobre a linha de
`virtual_campaign_slots`, dentro da transação, em **todos** os caminhos que mudam a posse do slot:
reservar, expirar, efetivar.

- **Reservar**: trava a linha, confere `status == 'livre'` (ou lock expirado), grava
  `locked_until = now + 15min` e o pedido dono. Concorrente que chega junto bloqueia no banco e,
  ao passar, encontra o slot tomado → 409 com a lista atualizada (US2 cenário 5).
- **Efetivar (webhook)**: trava a linha, reconsulta na operadora, e só então grava. Toda a
  orquestração (slot → evento → escala → fila 3D → estoque) roda numa transação só; qualquer falha
  desfaz tudo.
- **Idempotência**: `UNIQUE(order_nsu)` em `virtual_orders` e `UNIQUE(transaction_nsu)` em
  `virtual_payment_notifications`. Reentrega tenta inserir a notificação; violação de unicidade =
  já processado → responde `200 {"success": true}` sem reprocessar. O `200` é obrigatório: `400`
  faz a operadora reenviar em loop.
- **Expiração**: varredura por tarefa agendada + verificação preguiçosa na leitura dos horários
  (quem abre a landing já vê o slot livre). O caminho de expiração roda `payment_check` antes de
  liberar (FR-041a).

**Alternativa rejeitada**: lock otimista por versão — perde a corrida sem fila, e aqui a fila é o
comportamento desejado (o segundo visitante precisa saber que perdeu).

---

## R5. Autocomplete de endereço no checkout público

**Problema encontrado**: `app/api/maps_read.py:19` protege `/api/maps/address-autocomplete` com
`@api_login_required`, e o `GoogleAddressInput` vive em
`frontend/apps/internal/src/components/GoogleAddressInput.tsx` — **fora** do `@manto/ui`. O
checkout público não alcança nenhum dos dois hoje.

**Decisão**:
1. Promover `GoogleAddressInput` para `@manto/ui` e reapontar o app interno para o pacote — uma
   fonte só (Princípio I e XII.3). Copiar para `apps/public` está proibido.
2. Criar a variante pública do endpoint de autocomplete, sem login, com throttling por origem e
   restrita ao Brasil. A chave do Google continua no servidor (Princípio XII.4) e o debounce de
   350ms / mínimo 3 caracteres é mantido (XII.5).

---

## R6. Superfície pública — onde a landing mora

**Decisão**: rotas novas em `apps/public`, sob `/v/:slug` (campanha) e `/v/pedido/:token` (página
do pedido).

**Consequência a aceitar**: em produção, `apps/public` é servido sob o prefixo `/catalogo`
([frontend/server.js:34](frontend/server.js:34)) e o router usa `basename="/catalogo"`
([App.tsx:17](frontend/apps/public/src/App.tsx:17)). A URL pública real fica
`.../catalogo/v/<slug>`. Montar um quarto prefixo no `server.js` seria mais bonito na URL e mais
caro em build e risco; para um link distribuído por Instagram, o prefixo não atrapalha.

**Cuidado de rota**: `App.tsx` tem um catch-all `/:slug` para produto do catálogo. Rotas de dois
segmentos (`/v/:slug`) não colidem com ele, mas devem ser declaradas antes por clareza.

---

## R7. Registro financeiro segregado

**Decisão**: o evento gerado carrega `sale_value` e um marcador de canal novo; os agregadores
financeiros passam a filtrar por esse marcador.

**Achado**: `CalendarEvent` já tem `source` (`'google_calendar' | 'platform'`) e `event_type`
(`'SHOW'`, `'CORP'`, `'ENSAIO'`…). Um `event_type` novo (`'VIRTUAL'`) é o marcador mais barato e
já respeitado por quem consulta — e `app/impressoes3d/impressoes3d_ops.py:365` filtra a Fila 3D por
`event_type == EVENT_TYPE_SHOW`, então eventos virtuais **não** poluem a Fila 3D existente por
construção. A pendência de impressão do presente é criada explicitamente pelo nosso fluxo.

**Consequência a verificar na implementação**: todo agregador que soma eventos precisa decidir
sobre `'VIRTUAL'`. Os pontos são os painéis financeiro/DRE, KPIs e comissão — mapeados em tarefas
próprias, porque "esqueci um agregador" é exatamente como o KPI se distorce (FR-054).

---

## R8. Avisos por e-mail

**Decisão**: reusar `app/email_service.py`, que já tem envio assíncrono (`send_async`), wrapper de
HTML e o padrão de funções `send_*_email`. Acrescentar três funções no mesmo módulo.

**Achado**: não existe envio automatizado de WhatsApp em lugar nenhum do backend — só links
`wa.me` montados no front. A feature mantém isso: WhatsApp é reforço manual a um clique (FR-039b).

---

## Riscos residuais

| Risco | Impacto | Mitigação no plano |
|---|---|---|
| InfinitePay sem estorno por API | Devolução depende de pessoa | FR-041a previne o conflito; devolução rastreada até concluir |
| `createRequest` do Meet volta `pending` | Pedido pago sem sala | Reconciliação + pendência sinalizada; venda nunca cai |
| Vídeo escapar pela URL pública do storage | Exposição de dado de criança | FR-038e: só endpoint validado; subfolder fora do caminho estático; verificado em V7 |
| Banda/armazenamento no pico da campanha | Custo e lentidão | Volume sazonal e limite de tamanho por arquivo (FR-038d) |
| Caminho de sincronização esquecido | Evento pago corrompido | FR-029a exige cobrir todos os caminhos; V8 roda a sincronização completa |
| Operadora fora do ar na expiração | Horário retido ou conflito | Tolerância de 5 min com retry (FR-018a) e registro da decisão às cegas (FR-018b) |
| Documentação da InfinitePay incompleta | Contrato pode divergir | Cliente isolado num módulo só, com contrato versionado e teste contra sandbox |
