# CRM próprio da Manto — panorama e planejamento

> **Escrito em** 30/10/2026 · **Estado**: aprovado pelo dono ("bora iniciar"). **Fase 0 concluída** (§10).
> **Fase 1 implementada** em 30/10, na feature `325-crm-whatsapp-fundacao`: verify 22/22 e tela conferida. Ela está
> **sem publicar** e o módulo fica desligado até o app da Meta e as variáveis `WHATSAPP_*` (`docs/03` 325) ·
> **Fase 2a implementada** em 03/11, na feature `328-crm-equipe-na-caixa` (sobre a 325, também sem publicar):
> responsável com fila livre, alerta de cliente esperando (15 min, 9h–21h), notas internas, respostas rápidas e
> áudio gravado no navegador (`docs/03` 328) · **Fase 2b implementada** em 03/11, na feature
> `330-crm-instagram-direct` (sobre a 328, sem publicar): Instagram Direct na mesma caixa, ligado **pela Página do
> Facebook** (decisão do dono), só o Direct (sem comentários) · **Fase 2c implementada** em 03/11, na feature
> `332-crm-avisos-no-celular` (sobre a 330, sem publicar): a Plataforma instalável e o aviso no celular da mensagem
> nova da cliente, do alerta de 15 min e da transferência, a qualquer hora (decisões do dono); Web Push sem
> biblioteca de Web Push (só o `cryptography`, fixado), desligado até as chaves VAPID (`docs/03` 332) · **Fase 3a
> implementada** em 03/11, na feature `333-crm-orcamento-na-conversa` (sobre a 332, sem publicar): o orçamento
> (mensagem pronta e PDF) e o link do formulário saem pela conversa, das duas portas, e o orçamento fica ligado à
> ficha, que nasce na hora; "Criar evento" já traz a cliente. Decisão do dono: a Fase 3 em três fatias (3a
> orçamento/formulário, 3b origem do anúncio, 3c linha do tempo e funil) (`docs/03` 333) · **Fase 3b implementada**
> em 04/11, na feature `334-crm-origem-do-anuncio` (sobre a 333, sem publicar): o `referral` de quem clica no
> anúncio vira contato na conversa, a campanha vem da Meta (falta a permissão `ads_read`, `docs/05` 194) e a ficha
> guarda o primeiro e o mais recente anúncio; o Desempenho conta o lead da conversa e os retornos. Decisões do
> dono: perguntar a campanha à Meta, os dois anúncios (para a repescagem) e o canal como origem do orgânico
> (`docs/03` 334) ·
> **Base**: código em `main` `fe64252d` (citações conferidas contra o HEAD); números de volume do espelho
> de 30/09 (plano 6a, seção 3); documentação da Meta consultada em 30/10/2026 · **Antecede**: a memória
> de 29/06 ("WhatsApp CRM para substituir o Kommo").

## Contexto

O dono quer trocar o Kommo por um CRM dentro da Plataforma. Os motivos são três:

- **O app do Kommo é feio e ruim de usar.** No celular, só uma pessoa consegue mexer.
- **A licença anual pesa.**
- **Ele quer evoluir o comercial e o marketing.** O principal é **ver de qual campanha cada cliente
  veio** e automatizar o que hoje é manual.

As perguntas dele eram três: se é viável, se é arriscado ter o número banido (inclusive usando IA) e
qual é o plano.

## Veredito em cinco linhas

1. **É viável, e a Plataforma já tem metade da base.** Ela já tem clientes com o telefone como chave,
   orçamento, formulário, evento, webhooks, sino e mídia. Faltam o WhatsApp, o Direct, a caixa de
   conversas e as automações.
2. **O risco de banimento não aumenta por a tela ser nossa.** O que derruba um número é o
   comportamento: disparo em massa, denúncia e API não oficial. Na API oficial, respondendo a quem
   escreve primeiro, o risco é baixo, o mesmo de hoje.
3. **A IA é permitida, desde que seja a IA da Manto.** Desde 15/01/2026 a Meta proíbe assistente
   genérico ("estilo ChatGPT") como função principal do número. IA que atende o cliente da Manto sobre
   os serviços da Manto continua liberada.
4. **A economia da licença do Kommo não é o motivo principal.** A Meta cobra por mensagem com ou sem o
   Kommo. O ganho está na **atribuição de campanha, na integração e na automação**.
5. **O caminho é um módulo nativo na Plataforma, construído em fases.** O app do celular continua
   funcionando o tempo todo (coexistência), e o número principal só muda de lugar depois que tudo
   estiver provado num número de teste.

## Respostas do dono (30/10) e o que cada uma muda

| Resposta | O que muda |
|---|---|
| Um número só. Hoje 1 pessoa usa o app no celular e 1 usa o Kommo; às vezes abrem o WhatsApp Web. A ideia é 3 pessoas | Celular e Kommo funcionando juntos no mesmo número indica **coexistência**, que é oficial (o Kommo aparece como provedor dela). A outra possibilidade é conexão por QR code, que não é oficial. **A Fase 0 confirma qual das duas.** A régua de usabilidade passa a ser "tão fácil quanto o WhatsApp Web". |
| **Manter o app do celular** depois da virada | O caminho técnico é a **coexistência**. O app segue funcionando e a conexão traz cerca de **6 meses de histórico**, o que resolve o problema de o Kommo só exportar leads. Se a Plataforma cair, o celular continua atendendo. **Exigência da Meta:** só um *Tech Provider* ou um *Solution Partner* conecta número em coexistência (seção 6). |
| O Kommo recebe **Instagram Direct**, e quem responde são os mesmos vendedores | O Direct entra **na mesma caixa** que o WhatsApp. O Kommo só é cancelado quando o Direct estiver funcionando aqui. |
| Do Kommo se usa basicamente a conversa | A "paridade com o Kommo" encolhe para conversa boa mais atribuição. Funil manual não entra (seção 5). |
| 2 pessoas ao mesmo tempo, uns 20 clientes novos por dia | Cerca de 600 conversas novas por mês, volume pequeno para a infraestrutura atual. |
| Custo do Kommo desconhecido. Pagou R$ 700 na Meta (provavelmente anúncio). Acessa a conta da Manto pelo Facebook | A Fase 0 lê o faturamento do Kommo e separa, no Business Manager, o que é gasto de WhatsApp e o que é gasto de anúncio. |
| O CRM corre em paralelo ao backlog | As noites do backlog seguem. O CRM avança sem tocar a produção até a virada. |

## 1. Banimento: o que derruba número e o que não derruba

| Situação | Risco | Por quê |
|---|---|---|
| API oficial (Cloud API ou coexistência) com tela nossa | **Baixo, igual a hoje** | A Meta avalia o comportamento do número, não quem fez a tela. |
| Responder quem escreveu, dentro da janela de 24h | Muito baixo | É o uso principal da Manto. |
| Mensagem fora da janela sem template | Nenhum | A API recusa com erro. Não conta como infração. |
| Template de **utilidade** (lembrete do evento, pagamento, link do formulário) | Baixo | É a mensagem que o cliente espera. |
| Template de **marketing** em massa para a base antiga (6.251 clientes vindos do Kommo) | **Médio a alto** | Bloqueio e denúncia derrubam a nota de qualidade. Com a nota baixa, a Meta pausa template e limita envio. Essa base não tem opt-in claro. |
| API **não oficial** (Evolution, Baileys, WPPConnect, QR code de terceiros) | **Alto** | Viola os termos do WhatsApp, e o banimento vem sem recurso. **Nunca.** |
| IA genérica como função principal | **Proibido** | Termos de 15/01/2026 (seção 2). |

**Regra:** mensagem proativa só com motivo claro e frequência controlada, campanha só para quem
aceitou receber, e nada de API não oficial.

## 2. IA dentro do WhatsApp: o que a Meta permite desde 15/01/2026

A regra proíbe a IA quando ela é a função **principal** oferecida, "a critério exclusivo da Meta", e
não quando é **incidental** ao negócio. Segundo a imprensa, a Meta confirmou que o alvo são os
provedores de assistentes (ChatGPT, Perplexity), e não as empresas que usam IA para atender os próprios
clientes.

| Uso | Situação |
|---|---|
| **Copiloto do vendedor**: a IA sugere, resume e transcreve o áudio; quem envia é o vendedor | ✅ Risco zero de política |
| Tirar da conversa data, local, tipo de festa e convidados para pré-preencher a calculadora | ✅ Uso interno |
| Bot de primeiro atendimento da Manto (horário, pacotes, coleta de dados), passando para um humano | ✅ Permitido, com escopo fechado |
| Assistente que responde "qualquer coisa" | ❌ Proibido |
| Treinar modelo genérico com as conversas | ❌ Proibido. Ajustar um modelo só para uso da Manto é permitido |

**Proteções do desenho:**
- A IA é uma camada **desligável** por chave de configuração e fica fora do caminho crítico.
- O bot recusa assunto fora da Manto, se apresenta como atendimento automático e passa para um humano.
- O provedor de IA precisa ter contrato que não treina com os dados. É o padrão das APIs comerciais;
  confirmar no contrato.

A Meta vende uma IA de atendimento própria (Meta Business Agent, cerca de US$ 0,04–0,05 por mensagem).
Não precisamos dela.

## 3. Custos

- **Kommo (sai).** Cobra por usuário por mês:

  | Plano | Preço por usuário/mês |
  |---|---|
  | Básico | US$ 15–20 |
  | Avançado | US$ 25–30 |
  | Empresarial | US$ 45 |

  A alta de 01/09/2026 vale só para clientes novos; quem já é cliente mantém o preço antigo. O valor
  real sai da Fase 0.
- **Meta (fica, igual nos dois cenários).** Desde **01/10/2026** a Meta voltou a cobrar as respostas
  dentro da janela de 24h.
  - Cada número tem 1.000 mensagens grátis por mês. Acima disso, cerca de US$ 0,0068 por mensagem (≈
    R$ 0,035, segundo sites de terceiros).
  - Na coexistência, **o que sai pelo app do celular é grátis**. Só o que sai pela API é cobrado.
  - Com cerca de 600 conversas por mês, o gasto fica na casa de algumas centenas de reais por mês,
    conforme quantas mensagens saírem pela API.
  - Template de marketing ≈ R$ 0,32 por mensagem.
  - Conversa que começa por anúncio "abrir no WhatsApp" é grátis por uma janela (a documentação da
    Meta fala em até 7 dias).
  - **Divergência:** a página da Meta em português ainda diz que a resposta dentro da janela é grátis;
    a documentação técnica diz que é cobrada desde 01/10. Conferir na fatura.
- **Coexistência.** Ser *Tech Provider* próprio não tem mensalidade, só burocracia. Um intermediário
  (por exemplo, a 360dialog) cobra cerca de €49 por número por mês, segundo sites de terceiros.
- **Nosso CRM.**
  - Infraestrutura nova: quase nada. O Render já está pago, e a mídia vai para S3/R2.
  - IA: proporcional ao uso, medida no piloto.
  - **O custo de verdade é o tempo para construir e manter.** A Meta mudou preço e regra três vezes em
    2026.

## 4. O que já existe na Plataforma

**Dá para reaproveitar:**
- **Cliente.** `Client` com `phone` UNIQUE, `EventClient` e o importador do Kommo
  (`app/clientes/importer.py`, `normalize_phone`). Os campos `lead_stage`, `funnel`, `responsible` e
  `tags` estão gravados, mas nenhuma tela os usa.
- **Atribuição.** `Client.lead_origin` e `utm_*`, mais a tela Desempenho
  (`app/marketing/desempenho_ops.py`). No espelho de 30/09, **nenhum** cliente tem origem.
- **Webhook de entrada.** Há dois moldes:
  - `app/api/clicksign_webhook.py`: HMAC com `compare_digest` e troca de segredo.
  - `app/api/virtuais_webhook.py`: grava o aviso como pendente, processa numa thread e uma varredura
    reprocessa o que falhou.

  A Meta pede o mesmo, mais o handshake `hub.challenge` e a assinatura `X-Hub-Signature-256`.
- **Sino.** `emitir()` (`app/notificacoes/notificacoes_ops.py`), entregue por polling a cada 60s.
- **Mídia.** `save_file` (`app/storage.py`), em disco ou S3/R2.
- **Textos prontos.** A mensagem e o PDF do orçamento (`app/orcamento/`) e o link do formulário
  (`app/formularios/formularios_ops.py`). Hoje vai tudo por copiar e colar.
- **Ligação por telefone.** Formulário→cliente (`attempt_auto_link_client`) e formulário→evento
  (`_attempt_auto_link`).

**Falta:**
- cliente da Graph API e webhook da Meta;
- tabelas de conversa, mensagem e mídia;
- a caixa de conversas;
- etapas derivadas;
- motor de automações;
- SDK de IA;
- ligar o orçamento ao cliente (hoje `OrcamentoHistory.client_name` é texto livre).

**Limites da infraestrutura que pesam:**
- O proxy Node não passa websocket (só `proxy.web()`), então a primeira versão usa polling curto.
- O backend é uma instância só, por causa do disco, e cai alguns segundos a cada deploy.
- As threads morrem no deploy, e não há fila durável.
- São 36 threads do gunicorn (3 workers × 12), e a calculadora é a primeira a sentir carga.

## 5. A lição do CRM que já foi apagado

A feature 021 (junho) apagou um CRM de funil (Pipeline, Organizações, Negócios) que **ninguém usava**.
Nas palavras do dono: "Não estou usando agora e não quero que cause confusão".

**Princípio do novo CRM:** ele nasce na **conversa**, onde o trabalho já acontece, e o funil é
**derivado dos fatos**, sem cartão para arrastar. A sequência é conversa nova → orçamento enviado →
formulário → evento → venda → pagamento → avaliação. É o mesmo padrão das tarefas de casting.

## 6. Caminho técnico

- **Módulo nativo na Plataforma (decidido).**
  - Uma tela, um login, uma base de clientes e as mesmas permissões.
  - Orçamento, formulário, evento e marketing se ligam direto.
  - O Chatwoot (open source) fica como plano B, se a Fase 2 mostrar que a caixa de conversas dá mais
    trabalho do que parece.
- **Conexão do número principal em coexistência.** Há duas portas:
  - **A. Tech Provider próprio (recomendada).** São três etapas: verificação da empresa no Business
    Manager (de 2 a 5 dias úteis, às vezes semanas), App Review das permissões
    `whatsapp_business_messaging` e `whatsapp_business_management`, e o Embedded Signup com
    coexistência no nosso app. Não tem mensalidade nem intermediário. A papelada começa na Fase 1, em
    paralelo ao código.
  - **B. Intermediário como "cano"** (um provedor com coexistência e API crua, como a 360dialog). É
    mais rápido, mas cobra mensalidade e cria dependência. É a reserva se o App Review for negado ou
    atrasar até a renovação do Kommo.
  - **C. Conta de mensagens nossa no mesmo número, em paralelo ao Kommo** (novo modelo de contas da
    Meta, de 23/09/2026; ver seção 10). É a mais simples, se se confirmar que funciona com números em
    coexistência e que as mensagens recebidas chegam às duas contas. A confirmação fica para a Fase 1.
  - O código é praticamente o mesmo nas três portas.
- **Instagram Direct.** ~~API do Instagram com Instagram Login~~ → **pela Página do Facebook** (decisão do dono,
  03/11; feature 330): token do portfólio que não vence, roteamento da Meta que deixa o piloto conviver com o Kommo
  e o anúncio de origem no `referral`. Permissões `instagram_basic`, `instagram_manage_messages`,
  `pages_manage_metadata`, `pages_messaging` e a marca "Human Agent" (no mesmo App Review); janela de 24 h (7 dias
  com a marca humana) e a mesma caixa.
- **API não oficial: descartada.**

## 7. O que o CRM destrava, em ordem de dinheiro

1. **Follow-up de orçamento.** São cerca de 460 orçamentos por mês, e cerca de 9% viram evento (espelho
   de 30/09, plano 6a N5). Cada ponto percentual a mais dá 4 a 5 eventos por mês.
2. **Canal de campanha automático.** A primeira mensagem de quem clica num anúncio de WhatsApp ou do
   Direct chega com o ID do anúncio. Isso dá o custo por evento de cada campanha (o 6b). O 6a, a
   pergunta no formulário, continua valendo para quem não veio de anúncio.
3. **Tempo de primeira resposta e conversão por vendedor**, com aviso de lead esperando.
4. **Fim do copiar e colar.** Orçamento (mensagem e PDF) e formulário vão para a conversa, e o
   orçamento fica ligado ao cliente.
5. **Ficha única do cliente**, com uma linha do tempo de conversas, orçamentos, formulários, eventos,
   pagamentos e avaliações.
6. **Pós-evento e recompra.** Link de avaliação (feature 130) e lembrete no aniversário da festa, com
   opt-in.
7. **IA copiloto.** Resumo, sugestão de resposta, transcrição de áudio e pré-preenchimento da
   calculadora.

## 8. Plano por fases

Régua: a feature 303 teve 148 tarefas. Cada fase só começa quando o portão da anterior fica verde.

| Fase | O que entrega | Tamanho | Portão de saída |
|---|---|---|---|
| **0. Descoberta** (no Chrome, só leitura) | **Kommo:** plano, usuários, valor, renovação e como o WhatsApp e o Instagram estão ligados. **Gerenciador do WhatsApp:** portfólio dono da conta, situação do número (coexistência?), nota de qualidade, limite de envio, **verificação da empresa**, forma de pagamento e gasto de WhatsApp separado do de anúncio. | 1 sessão | Conexão confirmada como oficial e porta A ou B escolhida |
| **1. Fundação** (Nível 1), no **número de teste grátis da Meta** | App Meta no portfólio da Manto (o dono cria, eu guio). Webhook. Tabelas de conversa, mensagem e mídia. Download imediato da mídia (o link da Meta expira). Envio de texto, mídia, áudio e template. Status de entregue e lido. Tela mínima. Variáveis novas nascem desligadas (em produção, o endpoint responde 404 até ser configurado). A papelada de Tech Provider corre em paralelo. | ~1× a 303 | Conversa de ida e volta com áudio e foto, nenhuma mensagem perdida num deploy, verify verde |
| **2. Caixa de conversas** (Nível 1) — dividida pelo dono em 03/11: **2a equipe na caixa** (feature 328, feita), **2b Direct** (feature 330, feita), **2c push** (feature 332, feita) | WhatsApp e **Direct na mesma caixa**. Três usuários, "quem está atendendo", transferência, notas internas, respostas rápidas, busca e aviso de "sem resposta há X min". Sino e push no celular (PWA). Tela pensada primeiro para o celular, com gravação de áudio. A régua é o WhatsApp Web. | ~1× | Um vendedor atende um dia inteiro pelo número de teste sem sentir falta do Kommo |
| **3. Costura com a Plataforma** (Nível 1) — dividida pelo dono em 03/11: **3a orçamento e formulário** (feature 333, feita), **3b origem do anúncio** (feature 334, feita), 3c linha do tempo e funil | Conversa ligada ao cliente, linha do tempo na ficha, orçamento enviado na conversa e ligado ao cliente, link do formulário, funil derivado e **canal de campanha pelo anúncio** (alimenta o 6b). | ~1× | Um orçamento de verdade vai da conversa à venda sem copiar e colar |
| **4. Virada** (operação, à noite) | Desconectar o Kommo no app e conectar ao nosso em coexistência. Chegam cerca de 6 meses de histórico, e **o celular nunca para**. O Instagram passa para o nosso app (antes, testar se os dois apps recebem juntos). O Kommo fica só para consulta até o fim do contrato. Importação dos leads. | Código pequeno, risco operacional | Uma semana sem incidente; Kommo cancelado na renovação |
| **5. IA copiloto** (Nível 1) | Resumo, sugestão de resposta, transcrição, extração para a calculadora e nota do lead. **Quem envia é o humano.** Chave de liga e desliga. | ~0,5× | Uso e custo mensal medidos |
| **6. Automações e bot** (Nível 1) | Follow-up de orçamento, lembrete antes do evento, pós-evento e recompra com opt-in. Bot fora do horário, com escopo da Manto e passagem para humano. | ~1× | Nota de qualidade alta por 30 dias |

No total, de 4 a 5 vezes a 303, em paralelo às noites do backlog. As implantações entram no lote
noturno de sempre.

## 9. Riscos e como cada um se reduz

1. **O Kommo pode estar ligado por QR code, que não é oficial.** Nesse caso o risco de hoje é maior que
   o do projeto. A Fase 0 descobre.
2. **O App Review pode ser negado ou demorar.** A papelada começa cedo, e a porta B fica de reserva.
3. **Pode haver espera para trocar de provedor.** Uma fonte cita uma espera antes de reconectar um
   número em coexistência. Vamos medir ou perguntar à Meta antes da virada. Durante a espera, o celular
   segue funcionando.
4. **A Plataforma pode ficar fora do ar.** O celular é a reserva. O webhook grava a mensagem crua e
   responde rápido, e a Meta reenvia o que falhar. Atenção ao horário: quem contrata festa escreve à
   noite e no fim de semana, e a janela de deploy é a partir das 19h.
5. **Tempo real e carga.** Polling curto só na conversa aberta, com a carga medida. Se pesar, entra SSE
   ou um serviço pequeno.
6. **Adoção.** Tela pensada para o celular, push, áudio e piloto com quem mais atende.
7. **Campanha para a base antiga.** Só para quem aceitou receber, em lotes, acompanhando a nota de
   qualidade.
8. **LGPD.** Conversa é dado pessoal. Acesso só para Comercial e Superadmin, prazo de guarda definido e
   provedor de IA com contrato que não treina com os dados.
9. **A Meta muda as regras.** Versão da API fixa, revisão uma vez por ano e IA desligável.
10. **Custo em dobro na transição.** Mirar a virada antes da renovação do Kommo.

## 10. Registro da Fase 0 (30/10/2026, leitura no Chrome do dono, sem alterar nada)

**Kommo** (conta `crmamomantoproducoescombr`):
- **Faturamento → Meu plano:** plano Avançado (legado), US$ 25 por licença por mês, **1 licença**
  paga (1 de 1 em uso), válido até **13/02/2027**, renovação por parceiro. Nenhum complemento ativo.
  Isso dá **cerca de US$ 300 por ano**. Para 3 pessoas, seriam 3 licenças (pelo menos US$ 900 por
  ano, sem contar o preço novo).
- **Faturamento → Uso:**
  - leads: **7.813 de 10.000 (78%)**, com o aviso "Você está chegando ao seu limite";
  - contatos: 16.149 de 50.000;
  - números de WhatsApp: 1 de 3; contas de Instagram: 1 de 3;
  - pipelines: 4 de 50; campos personalizados: 46 de 400;
  - créditos de IA: 53 de 2.500.

  Com cerca de 600 leads novos por mês, o limite chega por volta de fevereiro de 2027, junto com a
  renovação: o upgrade seria obrigatório.
- **Menu:** Agente de IA (não ativado), WhatsApp Business, Instagram, Kommo Copilot (resumos de lead
  por IA). Na caixa de conversas também entram comentários do Instagram.
- **WhatsApp Business → Configurações:** o widget é `whatsapp_cloud_api`, ou seja, **API oficial**. O
  número **+55 11 97057‑0577** está com qualidade **Alta**, WABA "Manto Produções", conectado com o
  Facebook do dono.

**Meta** (portfólio "Manto Produções", ID 1404690356498847):
- **Informação do negócio:** razão social MONTA PRODUCOES E EVENTOS LTDA, CNPJ 32.623.682/0001-85.
  **Verificação do negócio: Verificado em 13/03/2026.** A autenticação de dois fatores é obrigatória
  no portfólio.
- **Contas do WhatsApp:** 1 conta, **propriedade de Manto Produções**. Status "Ligado", qualidade
  "Elevada", 3 pessoas com acesso total e **1 parceiro: Kommo**, com controle total.
- **Contas de mensagens:** "Manto Produções", tipo **"App WhatsApp Business"**. Isso confirma a
  **coexistência**: o número funciona no app do celular e na API ao mesmo tempo. Conta aprovada, em
  USD, com cartão cadastrado.
- **Aviso da Meta na tela:** "We've updated the account structure… to use the same phone number for
  multiple solutions." Pelo **novo modelo de contas** (lançado em 23/09/2026 e liberado para todas as
  empresas até meados de outubro), o **mesmo número aceita várias contas de mensagens**, uma por
  provedor ou integração, cada uma com a própria cobrança e os próprios templates. Ficam
  compartilhados entre elas a vazão e o limite de envio.
- **Gestor do WhatsApp → número → Estatísticas (02/10 a 29/10/2026):**

  | Indicador | Valor |
  |---|---|
  | Enviadas | 3.120 |
  | Entregues | 3.117 (marketing 23, serviço 3.094) |
  | Recebidas | 4.549 |
  | Grátis | 821 |
  | Pagas | 2.296 |
  | **Cobrança aproximada** | **US$ 17,00** (marketing US$ 1,44 · serviço US$ 15,56) |

  O valor bate com a tarifa de serviço de ~US$ 0,0068 por mensagem. Os R$ 700 que o dono pagou são de
  anúncio, não de WhatsApp.

**O que isso muda no plano:**
1. **Nenhum bloqueio.** A conexão é oficial, a conta é da Manto, a empresa está verificada e a
   qualidade está alta.
2. **Custo:** o Kommo custa ~US$ 300 por ano e a Meta ~US$ 17 por mês. **A economia não justifica o
   projeto.** O que justifica é:
   - a usabilidade para 3 pessoas (no Kommo, isso exige 3 licenças);
   - a atribuição de campanha;
   - a automação;
   - o limite de leads que vence junto com a renovação, em 13/02/2027.

   Esta é também a **data-alvo** da virada.
3. **Surge uma porta C, a mais simples:** uma **conta de mensagens nossa no mesmo número**, em
   paralelo ao Kommo, pelo modelo novo. Com ela não seria preciso virar Tech Provider nem desligar o
   Kommo para testar. **Há duas dúvidas a confirmar na Fase 1, antes de ligar no número principal:**
   (a) como a Meta reparte as mensagens recebidas entre as contas que dividem o número; (b) se isso
   vale para um número em coexistência. A porta A (Tech Provider) fica mais fácil com a empresa já
   verificada: falta só o App Review. A porta B continua de reserva.

## Fontes

- Meta, preços da plataforma: serviço cobrado desde 01/10/2026, 1.000 mensagens grátis, janela do
  anúncio e faturamento em reais.
  https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing
- Meta, coexistência (exige Tech Provider ou Solution Partner).
  https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users
- Meta, como virar Tech Provider.
  https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/get-started-for-tech-providers
- Meta, limites de envio e nota de qualidade.
  https://developers.facebook.com/documentation/business-messaging/whatsapp/upcoming-messaging-limits-changes/
- Telnyx, limites da coexistência. https://developers.telnyx.com/docs/messaging/whatsapp/coexistence
- Chakra, coexistência (o Kommo listado como provedor e o histórico de 6 meses).
  https://chakrahq.com/article/whatsapp-coexistence-faq-answers-details/
- TechCrunch, termos contra chatbots genéricos.
  https://techcrunch.com/2025/10/18/whatssapp-changes-its-terms-to-bar-general-purpose-chatbots-from-its-platform/
- Sky One, o critério de "função principal". https://www.skyone.solutions/en/whatsapp-restringe-ia-externa
- Kommo, preços a partir de 01/09/2026. https://www.kommo.com/br/blog/atualizacao-precos-kommo/
- ChatMaxima, cobrança de serviço no Brasil.
  https://chatmaxima.com/blog/whatsapp-service-message-pricing-october-2026/
- 360dialog, preços. https://docs.360dialog.com/docs/get-started/pricing
- Hora de Codar, o risco da API não oficial. https://horadecodar.com.br/evolution-api-vs-api-oficial-whatsapp/
