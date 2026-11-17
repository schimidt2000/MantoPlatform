# Pesquisa — 335 Linha do tempo da ficha e funil das conversas

As decisões de produto vieram do dono (spec, Clarifications); aqui está só o "como". O mapa das fontes (modelo, ligação
com a ficha, fuso) foi feito por leitura do código em 06/11.

## R1 — O primeiro contato da conversa

- **Decisão**: o menor momento entre as mensagens **recebidas** (`conversa_mensagens.direcao = 'recebida'`) e os
  contatos por anúncio (`conversa_anuncios`, inclusive a abertura do Instagram sem mensagem), por conversa. Uma
  agregação só (`UNION ALL` + `GROUP BY conversa_id`), com o índice `(conversa_id, momento)` que já existe.
- **Por quê**: `conversas.created_at` é quando a Plataforma viu a conversa; na virada (Fase 4) o histórico de seis
  meses chega de uma vez e todas nasceriam no mesmo dia. A mensagem da cliente carrega o momento de verdade.
- **Descartado**: guardar o primeiro contato numa coluna (migration e manutenção em três lugares do aviso, para uma
  leitura que o índice já resolve).

## R2 — A etapa mais avançada

- **Decisão**: para cada conversa da coorte, a etapa mais avançada entre: `orcamento` (envio pela conversa, 333, ou
  orçamento ligado à ficha, depois do primeiro contato), `formulario` (`FormResponse.client_id` da ficha, depois),
  `evento` (evento vivo da ficha via `EventClient`, criado depois), `pagou` (pagamento registrado num desses eventos
  ou no principal do grupo) e `avaliou` (avaliação de um desses eventos). Uma etapa conta quem chegou nela ou além.
- **Por quê**: o funil fica sempre decrescente, mesmo quando o orçamento foi pelo celular (coexistência) e só o evento
  aparece; "parou em" fica bem definido (é a etapa mais avançada).
- **Como**: a coorte (até alguns milhares) e depois uma consulta em lote por fato, com o máximo do momento por chave
  (conversa ou ficha) comparado ao primeiro contato em Python. Os eventos vêm por ficha (poucos por ficha); os
  pagamentos e as avaliações por conjunto de ids de evento.
- **Descartado**: etapas independentes (o funil cresceria de "Orçamento" para "Evento"); uma consulta SQL única com
  `EXISTS` por etapa (difícil de ler e de testar, sem ganho na escala).

## R3 — Período, fuso e dimensões

- O período é de datas de São Paulo (`inicio` e `fim`, inclusivos); vira o intervalo UTC `[inicio 00:00 SP, fim+1 00:00
  SP)` para comparar com o primeiro contato (UTC). Padrão: o mês corrente. Máximo de 366 dias.
- **Vendedor**: o `responsavel_id` atual da conversa (328); sem ele, "Sem responsável".
- **Campanha**: a do primeiro contato por anúncio da conversa (`AnuncioMeta.campanha_nome`); sem anúncio, "Sem
  anúncio"; com anúncio sem campanha conhecida, "Campanha desconhecida".
- **Canal**: `whatsapp` ou `instagram`.

## R4 — Quem parou em cada etapa

- A mesma coorte e a mesma regra; filtra a etapa mais avançada igual à pedida. Até 200 conversas, da que chegou mais
  recentemente para a mais antiga, com o nome (a ficha ou o perfil), o canal, o vendedor, o primeiro contato, a
  campanha e o id para "Abrir conversa".

## R5 — Os marcos da ficha

| Marco | Fonte | Momento | Link |
|---|---|---|---|
| Entrou na base | `clients.kommo_created_at` (São Paulo) ou `created_at` (UTC) | o da entrada | — |
| Primeiro contato | R1, por conversa da ficha | UTC | "Abrir conversa" (só Comercial/Superadmin) |
| Anúncio / publicação | `conversa_anuncios` das conversas da ficha (sem o `outro`) | UTC | — |
| Orçamento enviado | `orcamento_envios` das conversas da ficha e `orcamento_history.client_id`; um por orçamento, no primeiro envio | UTC | "Ver orçamento" (só Comercial/Superadmin) |
| Formulário | `form_responses.client_id` | UTC | — |
| Evento fechado | eventos vivos da ficha (`EventClient`) | `created_at` UTC | "Ver evento" |
| Pagamento | `event_payments` desses eventos e do principal do grupo | o PIX (`recebido_em`, São Paulo) ou o registro (UTC) | — |
| Avaliação | `client_feedbacks` desses eventos | UTC | — |

- Saída em ISO com fuso (`+00:00` ou `-03:00`): a tela formata no fuso de São Paulo.
- O evento cancelado (e o pagamento e a avaliação dele) fica de fora, como nas listas (312).
- Até 300 marcos, do mais novo para o mais antigo (uma ficha real tem dezenas).

## R6 — Acesso

- Funil e parados: `pode_conversas` no início da view (403 para os demais).
- Linha do tempo: `_require_vendas` da base de clientes; o núcleo recebe se a pessoa abre conversas e orçamentos e só
  então põe os links. O Financeiro vê os marcos e os valores de pagamento (já vê o total vendido na ficha).

## R7 — Verificação

- Molde do `verify_334`, mas sem Meta: tudo é semeado no banco (conversas, mensagens com o momento, anúncios,
  orçamentos e envios, formulários, eventos com `source="platform"`, pagamentos e avaliações) e lido pela API.
- Datas relativas a hoje em São Paulo, com o período personalizado explícito.
