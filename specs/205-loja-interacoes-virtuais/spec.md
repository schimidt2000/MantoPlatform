# Feature Specification: Loja de Interações Virtuais

**Feature Branch**: `205-loja-interacoes-virtuais`

**Created**: 2026-07-30

**Status**: Draft

**Input**: User description: "Canal de e-commerce B2C self-service para venda de interações virtuais (chamadas de vídeo de 10 min ao vivo e vídeos gravados) com personagens do catálogo, com checkout assíncrono via InfinitePay e automação total da entrega operacional"

## Clarifications

### Session 2026-07-30

- Q: Como a venda de uma interação virtual deve aparecer no financeiro da Manto? → A: Receita segregada por canal — o evento carrega o valor da venda marcado como canal "loja virtual", soma no DRE e num painel próprio da campanha, e fica fora por padrão dos KPIs de eventos e do cálculo de comissão.
- Q: Como os avisos à família (compra confirmada, vídeo pronto, cancelamento com estorno) devem ser disparados? → A: E-mail automático pelo serviço de e-mail já existente (e-mail passa a ser campo do checkout), com botão de WhatsApp pré-preenchido na fila para reforço manual.
- Q: Como o sistema deve validar que uma confirmação de pagamento veio mesmo da InfinitePay? → A: Assinatura do webhook validada E reconsulta da cobrança na API da InfinitePay antes de efetivar a venda (defesa em profundidade).
- Q: Como o sistema deve proteger o estoque de horários contra reservas em massa que nunca viram pagamento? → A: Uma reserva ativa por telefone de contato, somada a um teto de reservas por origem/sessão numa janela de tempo; excedentes recebem recusa explicativa.
- Q: Onde o vídeo gravado personalizado deve ficar hospedado para a família assistir? → A: Google Drive, automatizado — Vimeo exigiria assinatura paga. A produção envia o vídeo pela fila, o sistema o publica numa pasta do Drive da campanha e a família assiste pela página do pedido.

### Números fixados após o `/speckit.analyze` (2026-07-30)

Cinco ambiguidades apontadas pela análise, resolvidas com regras de negócio:

- **Upload de vídeo**: limite de **250 MB** por arquivo (FR-038d).
- **Sessão de acesso do pedido**: expira em **30 minutos** de inatividade (FR-044c).
- **Retry**: no máximo **3 tentativas espaçadas de 1 minuto** antes da falha definitiva, valendo para reconsulta de cobrança, e-mail e geração de sala (FR-056, FR-056a).
- **Status de produção**: exatamente **`pendente`, `gravando`, `finalizado`** — enviar o vídeo é ação, não estado (FR-048a).
- **Varreduras periódicas**: rotina de segundo plano dentro da própria aplicação, com execução única entre processos (FR-057, FR-057a, FR-057b).

**Consequência aritmética da política de retry**: as tentativas ocorrem em 0, 1 e 2 minutos após a
expiração, então a tolerância máxima é de **2 minutos** e o pior caso de devolução de um horário ao
estoque é de **17 minutos** (SC-005). O intervalo de 1 minuto foi escolhido deliberadamente para
manter a proteção contra vender horário já pago sem prender estoque no pico da campanha: 3
tentativas dão à operadora três chances de responder, e um horário nunca fica retido mais que 2
minutos além do soft lock.

### Blindagens aplicadas após o `/speckit.checklist` (2026-07-30)

Quatro lacunas que a auditoria de requisitos expôs, fechadas com decisões arquiteturais do projeto:

- **Privacidade do vídeo (CHK070)**: hospedagem migra do Google Drive para o armazenamento da própria plataforma, e todo conteúdo sensível do pedido passa a exigir **validação dupla** — identificador do pedido **e** telefone da compradora (FR-038e, FR-044a a FR-044c). O Drive foi descartado porque exigia liberar o vídeo para "qualquer pessoa com o link".
- **Sincronização (CHK062)**: eventos de interação virtual nascem marcados como criados na plataforma e a sincronização com a agenda externa passa a ignorá-los em todos os caminhos (FR-029a, FR-029b). A venda manda no evento, não a agenda externa.
- **Tolerância na expiração (CHK017)**: quando a operadora não responde na reconsulta exigida antes de liberar o horário, o sistema espera mais 5 minutos com novas tentativas antes de decidir (FR-018a, FR-018b). SC-005 passa a declarar os dois prazos.
- **Idempotência dos avisos (CHK027)**: o e-mail entra na lista do que não pode duplicar, com registro de disparo consultado antes do envio e gravado na mesma transação da decisão (FR-028, FR-028a, FR-028b).

### Revisões durante o `/speckit.plan` (2026-07-30)

Duas decisões acima foram ajustadas ao que a InfinitePay realmente oferece — a documentação pública descreve criação de link, webhook e `payment_check`, mas **não** assinatura de webhook nem API de estorno:

- **Autenticidade do pagamento**: a parte "validar assinatura" era inexequível. Fica a reconsulta obrigatória via `payment_check` como fonte de verdade (a intenção original — nunca confiar no aviso), somada a um endereço de notificação secreto e revogável. Ver FR-027a/FR-027b.
- **Estorno automático**: sem API de estorno, o sistema não pode devolver dinheiro sozinho. Passa a garantir que a devolução seja aberta, rastreada e cobrada até a conclusão, executada pela equipe. Em compensação, o conflito passa a ser prevenido na origem: o horário só é devolvido ao estoque depois de uma reconsulta que confirme que a cobrança não foi paga (FR-041a).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin monta e publica uma campanha virtual (Priority: P1)

A equipe comercial escolhe um Personagem ativo do catálogo e monta uma campanha de venda virtual: escreve os textos que a família vai ler (chamada, descrição, termos de tolerância, FAQ), escolhe a foto de capa, define os três preços (chamada ao vivo, vídeo gravado e adicional do presente 3D), gera o estoque de horários de 10 minutos para as chamadas, define quantos vídeos gravados cabem na campanha e em quantos dias eles são entregues, e seleciona quais peças do Acervo 3D podem ser oferecidas como presente. Ao publicar, a campanha ganha um endereço público próprio.

**Why this priority**: Sem campanha publicada não existe superfície de venda nem estoque — é o pré-requisito de todo o resto e, sozinha, já entrega valor (a equipe consegue montar e revisar a oferta antes de expor ao público).

**Independent Test**: Criar uma campanha ligada a um Personagem ativo, preencher textos/preços/estoque, publicar e abrir o endereço público num celular: a página aparece com os dados exatos que foram configurados, sem nenhuma venda existir ainda.

**Acceptance Scenarios**:

1. **Given** um Personagem ativo no catálogo, **When** o admin cria uma campanha vinculada a ele e preenche os campos obrigatórios, **Then** a campanha é salva como rascunho e ainda não é acessível publicamente.
2. **Given** uma campanha em rascunho com todos os campos obrigatórios preenchidos, **When** o admin publica, **Then** a campanha passa a ser acessível pelo endereço público e passa a aceitar reservas.
3. **Given** uma campanha publicada, **When** o admin gera horários informando data e janela de início/fim, **Then** o sistema cria os horários de 10 minutos dentro da janela, ignorando os que já existem (não duplica).
4. **Given** uma campanha publicada, **When** o admin altera um preço, **Then** o novo preço vale para reservas criadas a partir daquele momento e não altera pedidos já pagos.
5. **Given** uma campanha publicada, **When** o admin a despublica/pausa, **Then** o endereço público informa que a campanha não está disponível e nenhuma nova reserva é aceita.
6. **Given** uma campanha publicada, **When** o admin tenta remover um horário já reservado ou vendido, **Then** o sistema bloqueia a remoção e explica o motivo.

---

### User Story 2 - Família compra a interação sem falar com ninguém (Priority: P2)

Uma mãe recebe o link da campanha pelo Instagram, abre no celular, entende a oferta, escolhe entre "chamada de vídeo ao vivo de 10 minutos" ou "vídeo gravado", preenche os dados da criança (nome, idade, dicas de comportamento), o telefone e o e-mail de contato e o endereço, escolhe o horário (no caso da chamada) e é levada ao pagamento. O horário escolhido fica travado por 15 minutos enquanto ela paga.

**Why this priority**: É o coração do produto — o canal de receita self-service com atrito comercial zero. Testável isoladamente até a etapa de "pedido aguardando pagamento", mesmo antes da automação de entrega existir.

**Independent Test**: Em viewport de 375px, percorrer a landing de ponta a ponta, reservar um horário e chegar ao checkout: o horário some da lista para outros visitantes por 15 minutos e volta sozinho se o pagamento não for concluído.

**Acceptance Scenarios**:

1. **Given** uma campanha publicada com horários livres, **When** a família abre o endereço público num celular, **Then** vê capa, textos, preços em Real no padrão brasileiro, os horários disponíveis, o prazo de entrega do vídeo gravado e o FAQ apenas no final da página.
2. **Given** o formulário aberto, **When** a família tenta avançar sem preencher um campo obrigatório, **Then** o envio é bloqueado, o campo faltante é destacado e recebe o foco, e nada do que já foi digitado é perdido.
3. **Given** a família preencheu os dados e escolheu um horário, **When** confirma a reserva, **Then** o horário fica indisponível para os demais visitantes e a família vê quanto tempo resta para concluir o pagamento.
4. **Given** uma reserva com horário travado, **When** 15 minutos passam sem confirmação de pagamento, **Then** o horário volta a aparecer como disponível e a reserva é marcada como expirada.
5. **Given** dois visitantes simultâneos, **When** ambos tentam reservar o mesmo horário, **Then** apenas o primeiro consegue e o segundo recebe um aviso claro de que o horário acabou de ser tomado, com a lista de horários atualizada.
6. **Given** uma campanha cujo estoque de vídeos gravados acabou, **When** a família abre a página, **Then** a opção de vídeo gravado aparece como esgotada e não pode ser selecionada.
7. **Given** uma reserva confirmada, **When** a família é levada ao pagamento, **Then** o valor cobrado corresponde exatamente à soma dos itens escolhidos (interação + presente 3D, quando houver).
8. **Given** uma família que já tem uma reserva ativa, **When** tenta reservar um segundo horário com o mesmo telefone, **Then** o sistema recusa, mostra a reserva que ela já tem e oferece retomá-la ou abandoná-la.
9. **Given** uma mesma origem disparando reservas em sequência, **When** o teto da janela de tempo é atingido, **Then** as reservas seguintes são recusadas com explicação, os horários permanecem disponíveis para os demais e a tentativa fica registrada para a equipe.

---

### User Story 3 - Pagamento confirmado vira entrega operacional sozinho (Priority: P3)

Quando o pagamento é confirmado, ninguém da equipe precisa digitar nada: a reserva vira venda, o evento entra na Agenda no horário certo, a ficha preenchida pela família fica anexada a ele, o talento e o figurino do personagem já entram pré-escalados e o estoque é baixado.

**Why this priority**: É o que transforma o canal em "atrito zero". Sem isso a venda existe, mas alguém precisa transcrever pedido por pedido.

**Independent Test**: Disparar uma confirmação de pagamento para um pedido pendente e verificar, sem nenhuma ação humana, que o evento apareceu na Agenda com a ficha vinculada, com o talento pré-escalado e com o estoque atualizado.

**Acceptance Scenarios**:

1. **Given** um pedido aguardando pagamento, **When** a confirmação de pagamento chega, **Then** o pedido passa a "pago", o horário deixa de ser reversível e é criado um evento na Agenda no horário e na duração da interação.
2. **Given** o evento criado, **When** a equipe o abre na Agenda, **Then** encontra a ficha da criança (nome, idade, dicas), o telefone de contato e o endereço de entrega vinculados ao evento.
3. **Given** a campanha define talento e figurino do personagem, **When** o evento é criado, **Then** o talento entra pré-escalado com o figurino correspondente.
4. **Given** a mesma confirmação de pagamento é reentregue pela operadora, **When** ela chega novamente, **Then** o sistema reconhece que já processou e não cria evento, escala ou pendência duplicados.
5. **Given** uma notificação de pagamento forjada, sem origem comprovada, **When** ela chega no endereço público de notificação, **Then** o sistema a recusa e registra a tentativa, sem criar evento, escala, pendência 3D ou baixa de estoque.
6. **Given** uma notificação autêntica cuja cobrança, ao ser reconsultada na InfinitePay, aparece como não paga ou com valor diferente do pedido, **When** o sistema processa, **Then** a venda não é efetivada, a divergência é registrada e a equipe é avisada.
7. **Given** um pedido de vídeo gravado, **When** o pagamento é confirmado, **Then** o estoque de vídeos gravados da campanha é reduzido em uma unidade.
8. **Given** uma confirmação de pagamento chega para uma reserva cujo horário já expirou e foi vendido a outra pessoa, **When** o sistema processa, **Then** nenhum evento é criado, o pedido é cancelado, uma solicitação de devolução é aberta para a equipe executar e a família recebe automaticamente um e-mail explicando o cancelamento e a devolução em andamento.
9. **Given** uma solicitação de devolução aberta, **When** a equipe consulta o painel da campanha, **Then** ela aparece sinalizada com a cobrança e o valor, e continua sinalizada até alguém marcá-la como concluída — nunca é descartada em silêncio.
10. **Given** um soft lock que acabou de expirar, **When** o sistema vai devolver o horário ao estoque, **Then** ele antes reconsulta a cobrança na operadora e, se estiver paga, efetiva a venda em vez de liberar o horário.
11. **Given** um pedido pago de chamada ao vivo, **When** o evento é criado, **Then** o sistema gera uma sala de videochamada exclusiva daquele pedido e a entrega à família junto da confirmação.
12. **Given** um pedido pago, **When** a família conclui o checkout, **Then** ela vê a confirmação na tela e recebe automaticamente um e-mail com o resumo da compra, o horário contratado e o endereço da página do pedido.
13. **Given** uma família que acabou de pagar e voltou do checkout, **When** a confirmação ainda não chegou, **Then** ela aterrissa na página do pedido vendo "aguardando confirmação", e a página passa sozinha para "confirmado" quando a confirmação chega.

---

### User Story 4 - Upsell de presente 3D entra na fila de impressão sozinho (Priority: P4)

Durante o checkout, a família vê as peças do Acervo 3D liberadas para aquela campanha, cada uma com miniatura, e pode adicionar uma como presente por um valor extra. Ao confirmar o pagamento, a pendência de impressão nasce na Fila de Impressão 3D existente já vinculada ao evento, sem ninguém cadastrar nada.

**Why this priority**: É receita incremental sobre uma venda que já aconteceu e reaproveita um fluxo interno que já existe; pode ser entregue depois do canal estar vendendo.

**Independent Test**: Comprar uma interação com presente 3D e confirmar o pagamento: a peça escolhida aparece como pendência na Fila de Impressão 3D, vinculada ao evento e com o endereço de entrega acessível, sem intervenção manual.

**Acceptance Scenarios**:

1. **Given** uma campanha com peças 3D liberadas, **When** a família chega à etapa de presente, **Then** vê as peças liberadas com miniatura quadrada e consegue buscar pelo nome.
2. **Given** a família seleciona uma peça, **When** o resumo do pedido é exibido, **Then** o valor adicional do presente aparece somado ao total, no padrão brasileiro.
3. **Given** um pedido com presente 3D, **When** o pagamento é confirmado, **Then** a peça entra na Fila de Impressão 3D com status inicial "pendente", vinculada ao evento criado.
4. **Given** um pedido com presente 3D, **When** a família preenche o endereço, **Then** o endereço é validado por autocomplete e fica disponível para quem for despachar o presente.
5. **Given** uma campanha sem nenhuma peça 3D liberada, **When** a família percorre o checkout, **Then** a etapa de presente não aparece e o valor do presente não é cobrado.

---

### User Story 5 - Equipe de produção controla o que precisa ser gravado (Priority: P5)

O talento e a produção abrem uma tela tabular densa que mostra, em uma linha por entrega, tudo que precisam saber para executar: horário e modalidade (ao vivo ou gravado), nome da criança, as dicas que a família escreveu e o status de impressão do presente. Conforme trabalham, movem cada linha de `pendente` para `gravando` e depois `finalizado` — nas entregas ao vivo entrando pela sala da própria linha, nas gravadas enviando o vídeo pronto, que é o que libera a entrega para a família.

**Why this priority**: Sem essa tela a operação ainda funciona (os eventos estão na Agenda), mas com muita fricção; é a camada de eficiência sobre o que já foi automatizado.

**Independent Test**: Com pedidos pagos de ambas as modalidades, abrir a fila e confirmar que cada entrega aparece em uma linha com os quatro blocos de informação e que a mudança de status persiste após recarregar.

**Acceptance Scenarios**:

1. **Given** pedidos pagos de chamada ao vivo e de vídeo gravado, **When** a equipe abre a Fila de Produção de Mídia, **Then** vê uma linha por entrega com horário/modalidade, nome da criança, dicas da família e o status de impressão do presente 3D (ou a indicação de que não há presente).
2. **Given** uma entrega pendente, **When** o talento marca "gravando" e depois "finalizado", **Then** o status muda com feedback visual imediato e permanece após recarregar a página.
3. **Given** uma entrega de vídeo gravado, **When** a produção envia o vídeo pela fila, **Then** o sistema o guarda, confirma que ele é reproduzível, move a entrega para `finalizado` e dispara o e-mail de aviso — sem nenhum passo manual de link ou permissão.
4. **Given** o envio do vídeo falha, **When** a produção acompanha a fila, **Then** a entrega permanece em `pendente` ou `gravando`, o motivo aparece na linha, a família não é avisada e o envio pode ser repetido.
5. **Given** uma entrega finalizada, **When** a produção quer reforçar o aviso, **Then** encontra na própria linha um atalho de WhatsApp com a mensagem já preenchida.
6. **Given** uma entrega de vídeo gravado sem vídeo guardado, **When** alguém tenta movê-la para `finalizado`, **Then** o sistema bloqueia e explica que o vídeo precisa ser enviado antes.
7. **Given** uma entrega ao vivo, **When** o talento abre a linha no horário, **Then** encontra ali o acesso à sala daquele pedido.
8. **Given** muitas entregas cadastradas, **When** a equipe filtra por campanha, por data e por status, **Then** a lista responde ao filtro sem recarregar a página inteira.
9. **Given** uma entrega já finalizada, **When** a equipe consulta a fila do dia, **Then** consegue distinguir visualmente o que ainda falta do que já está pronto.

---

### Edge Cases

- **Pagamento fora da janela com horário ainda livre**: a confirmação chega depois dos 15 minutos, mas ninguém tomou o horário → o pedido é confirmado normalmente e o horário volta a ser travado.
- **Pagamento fora da janela com horário já vendido** → tratado no cenário 6 da US3: o pedido é cancelado e uma solicitação de devolução é aberta para a equipe executar.
- **Devolução pendente**: a solicitação fica aberta e sinalizada até a equipe executá-la e marcá-la como concluída — o dinheiro da família nunca fica sem dono no sistema.
- **Falha ao gerar a sala de videochamada**: a venda continua válida e a pendência aparece para a equipe; a sala pode ser gerada de novo ou informada manualmente antes do horário.
- **Vídeo gravado com prazo vencido**: a entrega é sinalizada à equipe e continua na fila, em `pendente` ou `gravando`, até o vídeo ser enviado.
- **Falha no envio do e-mail automático**: a venda e a entrega seguem válidas; a falha fica registrada no pedido e sinalizada à equipe, que reforça pelo atalho de WhatsApp.
- **Falha ao guardar o vídeo**: a entrega não é finalizada, a família não é avisada e a produção vê o motivo com a opção de tentar de novo.
- **Vídeo indisponível depois de entregue**: a família encontra um aviso na página do pedido em vez de um player quebrado, e a equipe é sinalizada.
- **Telefone errado na página do pedido**: a família vê que o telefone não confere e pode tentar de novo até o limite; esgotado o limite, o caminho é o WhatsApp da campanha.
- **Operadora indisponível na hora de expirar a reserva**: o horário fica retido por até 2 minutos extras enquanto as 3 tentativas acontecem; só então é liberado, com registro de que a decisão foi tomada às cegas.
- **Evento virtual editado ou apagado direto na agenda externa**: a sincronização não propaga a mudança; a equipe é sinalizada e o pedido pago segue valendo.
- **Arquivo grande ou conexão instável no envio**: o envio pode ser repetido sem duplicar o vídeo entregue nem criar uma segunda entrega.
- **Reentrega e ordem invertida de notificações**: a operadora pode reenviar a mesma confirmação ou entregar avisos fora de ordem; o processamento é idempotente e ignora transições retroativas.
- **Notificação de pagamento não reconhecida**: pagamento sem pedido correspondente é registrado para auditoria e sinalizado à equipe, nunca descartado em silêncio.
- **Notificação forjada ou sem o segredo do endereço**: recusada e registrada, sem tocar em estoque, agenda ou fila de impressão. Mesmo uma notificação que chegue pelo endereço certo só produz venda depois da reconsulta na operadora.
- **InfinitePay indisponível na hora de reconsultar**: o pedido fica retido para nova tentativa; a venda não é efetivada às cegas nem a notificação é perdida.
- **Campanha pausada com pedidos em aberto**: reservas já criadas continuam válidas até expirarem ou serem pagas; novas reservas são recusadas.
- **Estoque esgotado durante o checkout**: a última unidade de vídeo gravado é vendida enquanto outra família preenche o formulário → a segunda recebe aviso claro antes de ser mandada para o pagamento.
- **Horário no passado**: horários cuja hora de início já passou nunca aparecem como disponíveis, mesmo que nunca tenham sido vendidos.
- **Pedido sem presente 3D**: quando não há presente, o endereço de entrega não é exigido.
- **Idade fora da faixa esperada** (ex.: 0 ou acima de 18): o formulário aceita, mas sinaliza o valor atípico para a família confirmar.
- **Reserva abandonada e retomada**: a família volta ao link do pedido depois de expirado → vê que a reserva expirou e é convidada a escolher outro horário, com os dados já preenchidos preservados.
- **Preço alterado no meio de uma reserva ativa**: o pedido mantém os valores congelados no momento da reserva.
- **Campanha com horários que cruzam a meia-noite**: os horários são exibidos com a data correta, sem "vazar" para o dia seguinte na lista do dia.
- **Duplo clique no botão de reservar**: nunca cria duas reservas nem trava dois horários.
- **Tentativa de esvaziar o estoque**: reservas em massa de uma mesma origem são recusadas ao atingir o teto, e as recusas ficam registradas para a equipe perceber a investida.
- **Família legítima que trocou de ideia**: quem já tem reserva ativa e quer outro horário abandona a atual e reserva de novo, sem esperar os 15 minutos expirarem.
- **Duas crianças da mesma família**: como o limite é por telefone, a segunda compra só começa depois que a primeira for paga — comportamento aceito nesta versão.

## Requirements *(mandatory)*

### Functional Requirements

#### Gestão de Campanhas (Admin)

- **FR-001**: O sistema MUST permitir criar uma campanha virtual vinculada a um Personagem ativo do catálogo existente, sem duplicar o cadastro do personagem.
- **FR-002**: O sistema MUST permitir customizar o conteúdo público da campanha: título, texto de apresentação, termos de tolerância, itens de FAQ e foto de capa.
- **FR-003**: O sistema MUST permitir definir três preços independentes por campanha: valor da chamada ao vivo, valor do vídeo gravado e valor adicional do presente 3D.
- **FR-004**: O sistema MUST permitir gerar estoque de horários para chamadas ao vivo informando data e janela (início/fim), criando slots de 10 minutos e sem duplicar horários já existentes.
- **FR-005**: O sistema MUST permitir definir uma capacidade máxima finita de vídeos gravados por campanha, o prazo de entrega desses vídeos, e exibir quanto da capacidade já foi consumido.
- **FR-006**: O sistema MUST permitir selecionar quais peças do Acervo 3D existente ficam liberadas para oferta naquela campanha.
- **FR-007**: O sistema MUST permitir publicar, pausar e despublicar uma campanha; apenas campanhas publicadas aceitam novas reservas.
- **FR-008**: O sistema MUST impedir a exclusão de horários que já estejam reservados ou vendidos, explicando o motivo ao admin.
- **FR-009**: O sistema MUST exibir, por campanha, quantas interações foram vendidas, quanto foi faturado e quantos horários restam.
- **FR-010**: O acesso à gestão de campanhas MUST ser restrito aos perfis autorizados, seguindo o modelo de permissões já existente no sistema.

#### Superfície Pública e Checkout

- **FR-011**: O sistema MUST publicar cada campanha em um endereço público próprio, acessível sem login.
- **FR-012**: A superfície pública MUST ser mobile-first: funcionar sem rolagem horizontal de 320px a 430px, com alvos de toque de no mínimo 44px nas ações principais e sem texto informativo abaixo de 12px.
- **FR-013**: A landing MUST apresentar o FAQ apenas ao final da página, com um caminho explícito de contato por WhatsApp para o que o FAQ não resolver.
- **FR-014**: O sistema MUST coletar, por pedido: nome da criança, idade da criança, dicas de comportamento, telefone de contato, e-mail de contato e — quando houver presente 3D — endereço de entrega.
- **FR-015**: O endereço de entrega MUST ser preenchido por autocomplete de endereço validado, nunca por texto livre não verificado.
- **FR-016**: O sistema MUST oferecer o presente 3D como upsell no checkout, com busca por nome e miniatura quadrada de cada peça liberada.
- **FR-017**: Ao selecionar um horário, o sistema MUST aplicar um bloqueio temporário ("soft lock") de 15 minutos sobre aquele horário, impedindo que outro visitante o reserve.
- **FR-018**: O sistema MUST liberar automaticamente o horário quando o soft lock expira sem confirmação de pagamento, marcando a reserva como expirada.
- **FR-018a**: Se a reconsulta exigida antes da liberação não puder ser concluída (operadora indisponível), o sistema MUST aplicar a política de retry padrão (FR-056) antes de decidir, mantendo o horário retido enquanto tenta. Liberar um horário sem saber se ele foi pago é o que gera a venda em conflito — na dúvida, o sistema espera.
- **FR-018b**: Esgotadas as tentativas sem resposta da operadora, o sistema MUST liberar o horário, marcar a reserva como expirada e registrar que a decisão foi tomada sem confirmação — para que, se o pagamento aparecer depois, a equipe saiba a origem do conflito.
- **FR-019**: O sistema MUST exibir à família o tempo restante do soft lock durante o checkout.
- **FR-020**: O sistema MUST garantir que dois pedidos nunca ocupem o mesmo horário, mesmo com acessos simultâneos.
- **FR-020a**: O sistema MUST limitar a uma reserva ativa por telefone de contato; ao tentar uma segunda, a família MUST ser informada da reserva que já tem e poder retomá-la ou abandoná-la.
- **FR-020b**: O sistema MUST limitar quantas reservas uma mesma origem pode criar numa janela de tempo, recusando o excedente com explicação em vez de falhar em silêncio.
- **FR-020c**: As recusas por limite MUST ser registradas para que a equipe perceba tentativas de esvaziar o estoque.
- **FR-020d**: Os limites de reserva MUST ser ajustáveis pela equipe sem depender de nova entrega de código, para acomodar picos legítimos de campanha.
- **FR-021**: O sistema MUST encaminhar a família ao pagamento por link de pagamento da InfinitePay, com o valor total do pedido (interação + presente, quando houver).
- **FR-022**: O sistema MUST congelar os valores do pedido no momento da reserva; alterações de preço na campanha não afetam pedidos já criados.
- **FR-023**: O sistema MUST bloquear a seleção da modalidade "vídeo gravado" quando a capacidade da campanha estiver esgotada, informando o motivo.
- **FR-024**: Todo valor monetário exibido MUST seguir o padrão brasileiro (milhar com ponto, decimal com vírgula, duas casas).
- **FR-025**: Toda validação que bloqueia o envio MUST destacar o campo faltante, levar o foco até ele e preservar tudo o que já foi digitado.
- **FR-026**: Nenhum botão de ação MUST ficar sem resposta visual ao clique; cliques repetidos não podem gerar reservas ou cobranças duplicadas.

#### Automação Pós-Pagamento

- **FR-027**: O sistema MUST receber a confirmação de pagamento da InfinitePay de forma assíncrona e converter a reserva correspondente em venda efetivada.
- **FR-027a**: O endereço que recebe as notificações de pagamento MUST ser secreto e revogável, e o sistema MUST recusar e registrar chamadas que não o apresentem. A notificação MUST ser tratada como mero gatilho: nenhuma decisão de negócio pode ser tomada a partir do conteúdo dela.
- **FR-027b**: Antes de efetivar qualquer venda, o sistema MUST reconsultar a cobrança na InfinitePay e confirmar que ela está paga e que o valor confere com o total congelado no pedido — a notificação sozinha nunca basta para liberar produto.
- **FR-027c**: Se a reconsulta divergir da notificação (não paga, valor diferente, cobrança inexistente), o sistema MUST recusar a efetivação, registrar a divergência e sinalizá-la à equipe.
- **FR-027d**: Se a reconsulta estiver temporariamente indisponível, o sistema MUST reter o pedido para nova tentativa em vez de efetivar às cegas ou descartar a notificação.
- **FR-028**: O processamento da confirmação MUST ser idempotente: reentregas da mesma notificação não podem gerar eventos, escalas, pendências, baixas de estoque **nem avisos à família** duplicados.
- **FR-028a**: Cada tipo de aviso MUST ser enviado no máximo uma vez por pedido. O sistema MUST registrar o disparo e consultar esse registro antes de enviar — a garantia vem do registro, não da confiança em o fluxo não repetir.
- **FR-028b**: O registro de aviso enviado MUST ser gravado na mesma transação que decide o envio, para que uma falha no meio do processamento não deixe o pedido em estado que permita reenviar o mesmo aviso.
- **FR-029**: Ao confirmar o pagamento, o sistema MUST criar automaticamente um evento na Agenda no horário e na duração contratados, identificável como interação virtual e como tendo nascido na plataforma (não importado).
- **FR-029a**: A rotina de sincronização com a agenda externa MUST ignorar os eventos de interação virtual, em todos os seus caminhos — importação, atualização e remoção. A venda é a fonte de verdade desses eventos; deixar a sincronização reescrevê-los corromperia horário, título ou vínculo de um evento já pago.
- **FR-029b**: Um evento de interação virtual removido ou alterado diretamente na agenda externa MUST ser sinalizado à equipe em vez de propagar a mudança para o pedido — o pedido pago não pode ser desfeito por edição externa.
- **FR-030**: O sistema MUST vincular ao evento criado a ficha preenchida pela família (nome e idade da criança, dicas, telefone e endereço).
- **FR-031**: O sistema MUST pré-escalar automaticamente o talento e o figurino associados ao personagem da campanha no evento criado.
- **FR-032**: Quando o pedido incluir presente 3D, o sistema MUST criar automaticamente a pendência correspondente na Fila de Impressão 3D existente, vinculada ao evento e com status inicial "pendente", sem intervenção manual.
- **FR-033**: Quando o pedido for de vídeo gravado, o sistema MUST reduzir em uma unidade a capacidade disponível da campanha.
- **FR-034**: O sistema MUST registrar toda notificação de pagamento recebida — inclusive as não reconhecidas — para auditoria, e sinalizar à equipe as que não puderam ser processadas.
- **FR-035**: O sistema MUST confirmar a compra à família ao final do checkout e MUST enviar automaticamente um e-mail de confirmação, com resumo do que foi comprado, o horário contratado e o endereço da página do pedido.
- **FR-035a**: Ao voltar do pagamento, a família MUST aterrissar na página do pedido — nunca numa página em branco ou de erro. Como a confirmação do pagamento é assíncrona, essa página MUST mostrar o estado atual (aguardando confirmação ou já confirmado) e MUST se atualizar sozinha quando a confirmação chegar, sem a família precisar recarregar nem saber o que é um pagamento assíncrono.
- **FR-036**: Ao confirmar um pedido de chamada ao vivo, o sistema MUST gerar uma sala de videochamada exclusiva daquele pedido e disponibilizá-la tanto à família (na confirmação e na página do pedido) quanto ao talento escalado (no evento e na Fila de Produção de Mídia).
- **FR-037**: Se a geração da sala falhar, o sistema MUST manter a venda válida, sinalizar a pendência à equipe e permitir que a sala seja gerada novamente ou informada manualmente — a falha nunca pode cancelar a venda nem passar despercebida.
- **FR-038**: O vídeo gravado MUST ser entregue pela página do pedido: a produção envia o vídeo finalizado uma única vez e a família passa a assisti-lo por lá, sem baixar arquivo e sem precisar de conta.
- **FR-038a**: O envio do vídeo MUST ser automatizado de ponta a ponta a partir da fila: a produção escolhe o arquivo e o sistema o guarda no armazenamento da própria plataforma e o vincula ao pedido — sem ninguém copiar link, criar pasta ou ajustar permissão à mão.
- **FR-038b**: O sistema MUST verificar que o vídeo guardado está de fato reproduzível antes de dar a entrega por concluída e avisar a família.
- **FR-038e**: O vídeo MUST ser servido exclusivamente por um endereço que valide o acesso a cada requisição. Publicar o arquivo em um endereço de leitura direta — ainda que difícil de adivinhar — é proibido: um vídeo em que o nome da criança é dito em voz alta não pode depender de o endereço não vazar.
- **FR-038c**: Se o envio falhar, o sistema MUST manter a entrega em `pendente` ou `gravando`, explicar a falha à produção e permitir nova tentativa — nunca avisar a família de um vídeo que ela não consegue assistir.
- **FR-038d**: O sistema MUST recusar arquivos que não sejam vídeo ou que excedam **250 MB**, explicando o motivo no momento do envio.
- **FR-039**: Quando o vídeo gravado é disponibilizado, o sistema MUST enviar automaticamente um e-mail à família com o endereço da página do pedido.
- **FR-039a**: Quando um pedido é cancelado com estorno, o sistema MUST enviar automaticamente um e-mail à família explicando o cancelamento e a devolução — esse aviso nunca pode depender de ação humana.
- **FR-039b**: O sistema MUST oferecer, na Fila de Produção de Mídia e na tela do pedido, um atalho de WhatsApp com a mensagem já preenchida, para a equipe reforçar manualmente qualquer aviso.
- **FR-039c**: O sistema MUST registrar quais avisos automáticos foram enviados por pedido, e sinalizar à equipe as falhas de envio, para que o reforço manual seja feito com consciência do que falhou.
- **FR-040**: A campanha MUST definir o prazo máximo de entrega do vídeo gravado, e esse prazo MUST ser exibido na landing antes da compra e no resumo do pedido.
- **FR-041**: O sistema MUST sinalizar à equipe os pedidos de vídeo gravado cujo prazo de entrega esteja vencido ou por vencer.
- **FR-041a**: Antes de liberar um horário cujo soft lock expirou, o sistema MUST reconsultar a cobrança na operadora; se ela estiver paga, o pedido MUST ser efetivado em vez de o horário ser devolvido ao estoque. Prevenir o conflito é a defesa principal — o estorno é o último recurso.
- **FR-042**: Quando um pagamento é confirmado para um horário que já não está disponível, o sistema MUST cancelar o pedido e abrir uma solicitação de devolução, sem criar evento, escala ou pendência de impressão.
- **FR-043**: O sistema MUST registrar cada solicitação de devolução com o identificador da cobrança, o valor e o estado (pendente / concluída), e MUST sinalizá-la à equipe até que alguém a marque como concluída — nenhuma devolução pode ficar esquecida.
- **FR-043a**: O e-mail de cancelamento enviado à família MUST informar que a devolução está em andamento, sem prometer prazo que o sistema não controla.
- **FR-044**: A página pública do pedido MUST permitir que a família acompanhe seu pedido (situação, horário, acesso à chamada ou ao vídeo) sem login, por um endereço não adivinhável.
- **FR-044a**: O acesso a qualquer conteúdo sensível do pedido — nome e idade da criança, dicas, endereço, sala da chamada e vídeo — MUST exigir **duas** informações que só a compradora tem: o identificador do pedido e o telefone de contato informado na compra. O endereço sozinho MUST mostrar apenas o suficiente para a família saber que chegou ao pedido certo.
- **FR-044b**: A validação do telefone MUST resistir a tentativa em massa: erros consecutivos MUST ser limitados e registrados, para o telefone não virar um campo adivinhável.
- **FR-044c**: A sessão de acesso concedida após a validação MUST expirar em **30 minutos** de inatividade, para um dispositivo compartilhado não deixar os dados da criança abertos indefinidamente. Expirada a sessão, a família valida o telefone de novo.

#### Regras Transversais de Execução

- **FR-056**: Toda chamada a serviço externo que possa falhar por indisponibilidade MUST seguir a mesma política de retry: **no máximo 3 tentativas, espaçadas de 1 minuto** (a primeira imediata, as demais aos 1 e aos 2 minutos). Falhada a terceira, a falha é definitiva, registrada e sinalizada à equipe. Aplica-se à reconsulta de cobrança, ao envio de e-mail e à geração da sala de videochamada.
- **FR-056a**: A falha definitiva MUST ser sempre um estado explícito e visível, nunca um silêncio — quem depende da operação precisa conseguir descobrir que ela parou de tentar.
- **FR-057**: As rotinas de varredura periódica desta feature — expiração de reservas, retentativas pendentes e alerta de prazo de vídeo — MUST rodar como rotina de segundo plano dentro da própria aplicação, no mesmo padrão das varreduras que o sistema já opera, com intervalo configurável e sem depender de agendador externo.
- **FR-057a**: A varredura MUST garantir execução única mesmo com a aplicação rodando em vários processos — dois processos expirando a mesma reserva ao mesmo tempo é exatamente a corrida que o soft lock existe para evitar.
- **FR-057b**: Uma falha em um ciclo de varredura MUST ser registrada sem interromper os ciclos seguintes.

#### Fila de Produção de Mídia (Interno)

- **FR-045**: O sistema MUST oferecer uma listagem tabular densa das interações vendidas, com uma linha por entrega.
- **FR-046**: Cada linha MUST cruzar, na mesma altura: horário e modalidade (ao vivo ou gravado), nome da criança, dicas preenchidas pela família e o status de impressão do presente 3D (ou a indicação de que não há presente).
- **FR-047**: O sistema MUST permitir ao talento mover cada entrega pelo fluxo `pendente` → `gravando` → `finalizado`, com persistência imediata.
- **FR-048**: Para entregas de vídeo gravado, o sistema MUST permitir enviar o vídeo a partir da própria fila; a entrega só passa a `finalizado` depois que o vídeo está guardado e reproduzível. Sem vídeo, ela permanece em `pendente` ou `gravando`.
- **FR-048a**: Os únicos estados de produção MUST ser `pendente`, `gravando` e `finalizado`. Enviar o vídeo é a **ação** que permite chegar a `finalizado` — nunca um estado próprio.
- **FR-049**: Para entregas ao vivo, o sistema MUST exibir na linha o acesso à sala de videochamada daquele pedido.
- **FR-050**: O sistema MUST permitir filtrar a fila por campanha, por data e por status de produção.
- **FR-051**: O acesso à Fila de Produção de Mídia MUST respeitar o modelo de permissões existente, permitindo que o talento veja e atualize o que lhe cabe.

#### Registro Financeiro da Venda

- **FR-052**: O evento gerado por uma venda virtual MUST carregar o valor pago e MUST ser identificado como originado do canal "loja virtual", distinguível de qualquer outra venda do sistema.
- **FR-053**: A receita das vendas virtuais MUST somar no resultado financeiro da empresa (DRE) e MUST ser consultável por campanha.
- **FR-054**: As vendas virtuais MUST ficar fora, por padrão, dos indicadores de eventos (volume, ticket médio) e do cálculo de comissão de vendedor, sem que isso exija filtro manual de quem consulta.
- **FR-055**: Os painéis que hoje agregam eventos MUST permitir incluir explicitamente o canal "loja virtual" quando o usuário quiser ver o total consolidado.

### Key Entities

- **Campanha Virtual**: a oferta publicada de um Personagem. Guarda o vínculo com o personagem do catálogo, os textos públicos, a foto de capa, os três preços, o estado (rascunho / publicada / pausada), a capacidade de vídeos gravados e o endereço público.
- **Horário da Campanha (Slot)**: uma janela de 10 minutos vendável de uma campanha. Guarda data/hora de início, estado (livre / travado até um instante / vendido) e o pedido que o ocupa.
- **Acervo Liberado da Campanha**: relação entre a campanha e as peças do Acervo 3D existente que podem ser oferecidas como presente naquela campanha.
- **Pedido**: a intenção de compra de uma família. Guarda a modalidade (ao vivo ou gravado), o horário (quando aplicável), a peça 3D escolhida (quando houver), os valores congelados, o estado (reservado / aguardando pagamento / pago / expirado / cancelado-estornado / estorno pendente), o instante de expiração do soft lock, o endereço público de acompanhamento e a referência do pagamento.
- **Acesso à Interação**: o que a família recebe depois de pagar — a sala de videochamada exclusiva do pedido (ao vivo) ou o vídeo finalizado enviado pela produção (gravado). Os dois só são alcançáveis pela página do pedido, após a validação dupla (identificador + telefone).
- **Solicitação de Estorno**: o registro do estorno pedido à operadora quando um pagamento chega para um horário indisponível, com o resultado (concluído ou pendente de resolução manual).
- **Ficha da Criança**: os dados que a família preenche — nome e idade da criança, dicas de comportamento, telefone e e-mail de contato e endereço de entrega. Nasce junto do pedido e é vinculada ao evento gerado.
- **Aviso Enviado**: o registro de cada e-mail automático disparado para um pedido (confirmação, vídeo pronto, cancelamento) e seu resultado. Além de mostrar o que a família recebeu, é a **trava** que impede o mesmo aviso de sair duas vezes: no máximo um registro por pedido e tipo de aviso.
- **Registro de Notificação de Pagamento**: cada aviso recebido da operadora, com o identificador da cobrança, o conteúdo bruto, o resultado da verificação de autenticidade, o resultado da reconsulta na operadora e o desfecho do processamento — base da idempotência, da segurança e da auditoria.
- **Entrega de Mídia**: a unidade de trabalho da Fila de Produção — deriva de um pedido pago e carrega o status de produção (`pendente` / `gravando` / `finalizado`, os três únicos), o prazo de entrega (quando gravado), a referência do vídeo guardado e o resultado da última tentativa de envio.
- **Evento da Agenda** *(existente)*: o registro operacional criado pela automação, onde a escala de talento, o figurino e o presente 3D se conectam. Carrega o valor pago e a marca do canal "loja virtual", que é o que o separa das vendas de shows nos indicadores.
- **Pendência de Impressão 3D** *(existente)*: a linha da Fila de Impressão 3D criada automaticamente quando o pedido inclui presente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma família conclui a compra completa — da abertura do link ao pagamento — em menos de 5 minutos, no celular, sem falar com nenhum atendente.
- **SC-002**: 100% dos pagamentos confirmados geram evento na Agenda, ficha vinculada e pré-escala do talento sem qualquer digitação manual da equipe.
- **SC-003**: 100% dos pedidos com presente 3D aparecem na Fila de Impressão 3D em até 1 minuto após a confirmação do pagamento.
- **SC-004**: Zero horários vendidos em duplicidade, mesmo em picos com múltiplos visitantes disputando o mesmo horário.
- **SC-005**: Horários de reservas não pagas voltam a ficar disponíveis em no máximo 16 minutos após a reserva — ou 17 minutos no pior caso, quando a operadora está indisponível e as 3 tentativas da política de retry se esgotam.
- **SC-006**: Reentregas da mesma confirmação de pagamento não produzem nenhum registro duplicado (evento, escala, pendência 3D ou baixa de estoque), verificado com reprocessamento repetido.
- **SC-007**: A equipe monta e publica uma campanha nova, com estoque de horários de um dia inteiro, em menos de 10 minutos.
- **SC-008**: A landing pública funciona sem rolagem horizontal de 320px a 430px de largura.
- **SC-009**: Ao final da primeira campanha, no máximo 10% dos pedidos exigem intervenção manual da equipe (conflito, dado faltante ou correção).
- **SC-010**: O talento localiza e atualiza o status de qualquer entrega do dia na Fila de Produção de Mídia em menos de 15 segundos.
- **SC-011**: 100% dos pedidos ao vivo pagos têm o acesso à chamada disponível para a família e para o talento antes do horário contratado.
- **SC-012**: 100% dos pagamentos que caem em horário indisponível abrem uma solicitação de devolução rastreada, sem que nenhum deles crie evento ou pendência de impressão — e a reconsulta antes da expiração mantém esses casos abaixo de 1% dos pedidos pagos.
- **SC-013**: 100% dos vídeos gravados são entregues dentro do prazo publicado na campanha, e a família é avisada assim que o vídeo fica disponível.
- **SC-014**: A receita total de uma campanha, somada no painel da campanha, bate exatamente com o que entrou no DRE do período — e os indicadores de volume e ticket médio de eventos permanecem iguais aos de antes da campanha existir.
- **SC-015**: Nenhuma venda é efetivada sem que a cobrança tenha sido confirmada como paga direto na operadora; notificações forjadas ou divergentes produzem zero eventos, escalas, pendências 3D ou baixas de estoque.
- **SC-016**: Uma tentativa automatizada de reservar todos os horários de uma campanha é barrada antes de tornar a loja indisponível, e nenhuma família comprando normalmente esbarra nos limites.
- **SC-017**: A produção entrega um vídeo gravado em um único passo — escolher o arquivo — sem tocar em pasta, link ou permissão, e 100% dos vídeos avisados à família abrem de primeira no celular.
- **SC-018**: Nenhum dado de criança (nome, idade, dicas, endereço, vídeo) é alcançável sem apresentar identificador do pedido **e** telefone da compradora — verificado tentando acessar cada conteúdo apenas com o endereço.
- **SC-019**: Nenhum evento de interação virtual é alterado ou removido pela sincronização com a agenda externa, verificado rodando a sincronização completa após uma campanha com vendas.
- **SC-020**: Cada tipo de aviso chega no máximo uma vez por pedido, mesmo com a notificação de pagamento reentregue repetidamente.

## Assumptions

- **Reaproveitamento do catálogo**: as campanhas se apoiam nos Personagens já cadastrados no catálogo; esta feature não cria um cadastro paralelo de personagens.
- **Reaproveitamento do Acervo e da Fila 3D**: o presente 3D usa o Acervo 3D e a Fila de Impressão 3D que já existem; a automação apenas injeta a pendência no fluxo atual, sem criar uma segunda fila.
- **Reaproveitamento da Agenda**: a venda gera um evento na Agenda existente, identificado como interação virtual, criado direto na plataforma (sem depender de sincronização com o Google Calendar).
- **Talento e figurino**: a campanha define qual talento e qual figurino atendem aquele personagem; é isso que a automação usa na pré-escala. Se o personagem já estiver vinculado a uma ficha de figurino no catálogo, esse vínculo é o padrão sugerido.
- **Duração fixa**: toda chamada ao vivo dura 10 minutos; a feature não prevê durações variáveis nesta versão.
- **Vídeo gravado sem horário**: o vídeo gravado consome capacidade da campanha, não horário; sua execução é agendada pela produção dentro do prazo comunicado, e é a produção quem decide quando gravar.
- **Sala de videochamada**: a sala é gerada por pedido pelo sistema, é o canal oficial da chamada, e vale só para aquele horário. A escolha da ferramenta de videochamada é decisão de arquitetura (`/speckit.plan`), não de produto.
- **Hospedagem do vídeo gravado**: os vídeos ficam no armazenamento da própria plataforma, reaproveitando a camada de arquivos já usada por todo o sistema. Vimeo foi descartado por exigir assinatura paga; o Google Drive, cogitado na clarificação, foi descartado na revisão de privacidade — a liberação "qualquer pessoa com o link" que ele exige é incompatível com um vídeo em que o nome da criança é dito em voz alta.
- **Vídeo nunca tem endereço de leitura direta**: o arquivo é servido por um endereço que valida a cada requisição. Isso vale mesmo que o armazenamento subjacente saiba servir arquivos publicamente — nesse caso o endereço público não é usado nem divulgado.
- **Retenção dos vídeos**: os vídeos entregues permanecem disponíveis enquanto a campanha estiver ativa; a política de expurgo depois disso não faz parte desta versão.
- **Canal de aviso**: os avisos automáticos saem por e-mail, usando o serviço de e-mail que a plataforma já opera — não existe envio automatizado de WhatsApp no sistema hoje, e esta feature não cria um. O WhatsApp continua sendo reforço manual, a um clique, a partir da fila.
- **Avisos sempre apontam para a página do pedido**: nem o vídeo nem o acesso à sala circulam soltos por mensagem; o aviso leva à página do pedido, que é a fonte de verdade.
- **Pagamento é a única forma de confirmação**: não existe reserva "para pagar depois"; sem confirmação de pagamento no prazo, o horário volta ao estoque.
- **Devolução no conflito de horário é registrada pelo sistema, executada pela equipe**: a InfinitePay não publica API de estorno (levantado no `/speckit.plan`), então o sistema garante que a devolução seja aberta, rastreada e cobrada até a conclusão — mas quem devolve o dinheiro é uma pessoa, no painel da operadora. Desistência, atraso e no-show seguem a política de tolerância publicada na landing.
- **Confiança no aviso de pagamento**: a InfinitePay não assina seus webhooks. A garantia não vem do aviso, e sim da reconsulta da cobrança na operadora antes de liberar qualquer produto; o endereço de notificação secreto serve só para reduzir ruído.
- **Sem cálculo de frete**: o valor adicional do presente 3D já cobre o envio; a feature não calcula frete por endereço.
- **Uma peça 3D por pedido**: o upsell permite escolher uma peça por pedido nesta versão.
- **Pagamento é assíncrono por natureza**: a confirmação pode chegar segundos ou minutos depois do pagamento; a experiência da família não depende de resposta imediata na tela.
- **Idioma e moeda**: toda a superfície pública e interna fala pt-BR e opera em Real.
- **Dados de criança são sensíveis**: nome, idade e endereço coletados ficam restritos a quem opera a entrega e não são expostos em superfícies públicas.
- **Dependências externas**: a feature depende da InfinitePay para gerar cobranças e notificar confirmações; do serviço de autocomplete de endereço já usado pelo sistema; da agenda externa para gerar a sala da chamada; e do serviço de e-mail já operado pela plataforma. A hospedagem de vídeo deixou de ser dependência externa.
- **Eventos virtuais não são sincronizados**: nascem na plataforma e são marcados como tal. A sincronização com a agenda externa os ignora nos dois sentidos — é a venda, não a agenda externa, que manda nesses eventos.
