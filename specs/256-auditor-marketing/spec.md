# Feature Specification: Auditor de marketing semanal e mensuração no ERP

**Feature Branch**: `256-auditor-marketing`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Auditor de marketing semanal + mensuração de marketing no ERP (Instagram orgânico, Meta Ads e Google Ads), SEM API do Claude. A Manto posta no Instagram e roda campanhas no Google Ads e Meta Ads mas quase não acompanha resultado; o dono quer uma auditoria semanal automatizada, no padrão do auditor financeiro (feature 221), com relatório por e-mail e tela no ERP, e com o gasto de anúncios do cartão pessoal indo automaticamente para reembolso, com detalhe por campanha."

## Visão Geral

A Manto investe em três frentes de marketing — posts orgânicos no Instagram, impulsionamento no Meta Ads e campanhas no Google Ads — e não mede quase nada disso. Não há gente para acompanhar, então o marketing "parece fraco por ser pouco mensurado". As plataformas já entregam os números; o que falta é alguém juntar tudo, toda semana, e dizer em uma página o que aconteceu, o que custou e o que rendeu.

A feature cria o **auditor de marketing semanal**: uma rotina que roda toda segunda-feira cedo, no mesmo molde do auditor financeiro (feature 221) — sem custo por uso, a partir de arquivos exportados das plataformas e salvos numa pasta do computador do dono —, cruza esses números com o que o ERP já sabe (painel de postagens, metas de frequência, clientes novos, gastos) e entrega o resultado de duas formas: um **relatório por e-mail** com gráficos e uma **tela no ERP** ("Marketing → Desempenho") com o histórico.

A diferença de postura em relação ao auditor financeiro é deliberada e única: **esta rotina escreve uma coisa no ERP** — o gasto de anúncios do período, que hoje sai do cartão pessoal do dono, entra sozinho como Gasto Extra de Marketing para reembolso, com o valor aberto por campanha. Tudo o mais continua somente leitura.

### Decisões de produto já tomadas (dono, 2026-08-20)

1. **Entrada de dados = pasta local.** Os exports (CSV) da Meta e do Google são salvos manualmente numa pasta do computador onde a rotina roda. Upload pela interface do ERP e leitura automática de e-mail ficam para uma fase futura.
2. **Três canais**: Google Ads, Meta Ads (impulsionamento) e Instagram orgânico (os posts planejados no painel de marketing do ERP).
3. **Entrega dupla**: e-mail semanal com gráficos embutidos **e** tela no ERP com histórico — as duas lendo o mesmo histórico guardado no sistema.
4. **Gasto de anúncios vai automaticamente para reembolso.** A rotina calcula o gasto do período a partir dos relatórios das plataformas e cria o Gasto Extra (categoria Marketing, desembolso por reembolso ao dono), preservando o **detalhe por campanha** — não só o total.
5. **Sem custo por uso.** Roda na máquina do dono pela assinatura já existente; se o computador estiver desligado no horário, roda assim que ligar.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Relatório semanal a partir dos exports (Priority: P1)

Toda semana o dono (ou alguém do marketing) exporta os relatórios da Meta (insights de conteúdo, insights da conta, campanhas do Gerenciador de Anúncios) e do Google Ads (campanhas) e salva os arquivos na pasta combinada. Na segunda de manhã a rotina lê a pasta, reconhece cada arquivo, guarda os números e manda por e-mail um relatório em português com: o que foi publicado na semana e se as metas de frequência foram cumpridas, os 3 melhores e os 3 piores posts, crescimento de seguidores, gasto por plataforma e por campanha com custo por clique e por lead, e uma lista clara do que ficou sem dado (arquivo faltando, arquivo não reconhecido).

**Why this priority**: é o coração do pedido — "alguém que acompanhe". Sem esta história nada mais tem valor; com ela sozinha o dono já sai do escuro.

**Independent Test**: salvar um conjunto de exports reais de uma semana na pasta, disparar a rodada e verificar que o e-mail chega com todos os blocos preenchidos a partir desses arquivos, e que a ausência de um dos arquivos aparece nomeada no bloco "sem dado" em vez de sumir em silêncio.

**Acceptance Scenarios**:

1. **Given** a pasta contém os exports da semana nos formatos esperados, **When** a rodada de segunda executa, **Then** o dono recebe um e-mail com resumo da semana, posts × metas, ranking de posts, gasto por campanha e o bloco "sem dado" vazio.
2. **Given** falta o export do Google Ads, **When** a rodada executa, **Then** o relatório é enviado mesmo assim, com todas as seções da Meta preenchidas e a seção de Google marcada como "sem arquivo nesta semana" — nenhum número de Google é inventado ou repetido da semana anterior.
3. **Given** um arquivo da pasta não é reconhecido (colunas inesperadas, idioma diferente), **When** a rodada executa, **Then** o arquivo é listado no relatório pelo nome com o motivo da rejeição e o restante da rodada segue normalmente.
4. **Given** o mesmo arquivo foi salvo duas vezes (ou um export cobre dias já processados), **When** a rodada executa, **Then** nenhum número é contado em dobro — o histórico guarda um único valor por plataforma, item e dia.
5. **Given** o computador estava desligado na segunda às 06h, **When** ele é ligado mais tarde no mesmo dia, **Then** a rodada executa automaticamente e o relatório sai com a janela correta (da última rodada até agora).

---

### User Story 2 - Gasto de anúncios vira reembolso sozinho, com detalhe por campanha (Priority: P2)

O gasto com Meta Ads e Google Ads sai do cartão pessoal do dono. Hoje quase nada disso é lançado no ERP. A partir dos relatórios das plataformas, a rotina apura o gasto do **mês civil** por plataforma e por campanha e mantém no ERP **um Gasto Extra por plataforma e mês**, de categoria Marketing, com desembolso por reembolso ao dono e o valor de cada campanha guardado junto. Enquanto o gasto está pendente, as rodadas seguintes atualizam o valor conforme o mês avança; depois de aprovado ele congela. Se já existe um gasto de marketing lançado manualmente para o mesmo mês e plataforma, a rotina não cria outro: compara os valores e, se divergirem, aponta a diferença no relatório. O gasto nasce **sem comprovante** — a fatura do cartão ainda não existe na hora da rodada — e o relatório lembra o financeiro de anexá-la antes de aprovar.

**Why this priority**: é a parte que mexe com dinheiro e foi pedida explicitamente ("quero que vá automaticamente para reembolso"). Depende da leitura dos arquivos (US1), mas entrega valor próprio: o dono para de ficar sem ressarcimento por esquecer de lançar.

**Independent Test**: com um export de campanhas de uma semana na pasta, rodar e verificar que aparece um Gasto Extra de Marketing pendente, no valor do mês até ali, com o detalhamento por campanha visível ao abrir o gasto; rodar de novo com mais dias e verificar que o mesmo gasto é atualizado e que não surge um segundo.

**Acceptance Scenarios**:

1. **Given** os exports de campanhas da Meta e do Google trazem gasto no mês corrente e não há gasto de marketing lançado para esse mês, **When** a rodada executa, **Then** surge um Gasto Extra por plataforma e mês, categoria Marketing, desembolso "reembolso" ao dono, pendente e sem comprovante, com o detalhe por campanha anexado e o relatório/arquivo de origem identificados.
2. **Given** o gasto do mês já existe (pendente) para a mesma plataforma, **When** a rodada seguinte traz mais dias do mês (ou repete, em catch-up ou com arquivo reenviado), **Then** nenhum gasto novo é criado — o existente é atualizado com o valor acumulado e as linhas por campanha refeitas.
3. **Given** alguém já lançou manualmente um gasto de Marketing com competência no mês e a plataforma no nome, ou o gasto gerado já foi aprovado/rejeitado, e o valor difere do que as plataformas reportam, **When** a rodada executa, **Then** nenhum gasto novo é criado, o existente não é alterado e o relatório traz um achado "valor lançado R$ X × reportado pela plataforma R$ Y".
4. **Given** o export de campanhas traz valores em moeda diferente de real, **When** a rodada executa, **Then** nenhum gasto é criado para aquele arquivo e o relatório explica o motivo.
5. **Given** o gasto foi criado pela rotina, **When** o responsável financeiro abre o Gasto Extra no ERP, **Then** vê que foi gerado pelo auditor de marketing, de qual arquivo/rodada veio e o quanto cada campanha pesou — e aprova, edita ou rejeita como qualquer outro gasto.

---

### User Story 3 - Tela "Marketing → Desempenho" no ERP (Priority: P3)

Quem tem acesso ao marketing no ERP (papel Marketing e superadmin) abre uma tela com o histórico do que a rotina guardou: série semanal de alcance e seguidores, barras de gasto por campanha, funil gasto → cliques → leads → eventos fechados, tabela de posts com suas métricas e a lista de rodadas executadas (com o que cada uma rejeitou). É a memória que o e-mail não tem: comparar semana contra semana, mês contra mês.

**Why this priority**: o e-mail resolve a rotina; a tela resolve a análise. Foi pedido explicitamente ("os dois"), mas só tem valor depois que há histórico guardado.

**Independent Test**: após duas rodadas com dados, abrir a tela e verificar que os gráficos mostram as duas semanas, que a tabela de posts lista os posts com métricas e que a lista de rodadas bate com os e-mails enviados; abrir como um papel sem acesso a marketing e verificar que a tela não aparece nem responde.

**Acceptance Scenarios**:

1. **Given** há rodadas guardadas, **When** um usuário de Marketing abre a tela, **Then** vê gráficos das últimas 12 semanas, pode trocar o período e ver a tabela de posts e campanhas.
2. **Given** nenhuma rodada rodou ainda, **When** a tela é aberta, **Then** explica o que é preciso fazer (onde salvar os exports e quando a rotina roda) em vez de mostrar gráficos vazios.
3. **Given** um usuário sem papel de Marketing nem superadmin, **When** tenta acessar a tela ou os dados dela, **Then** é barrado como nas demais telas de marketing.
4. **Given** a tela é aberta no celular, **When** carrega, **Then** os gráficos e tabelas continuam legíveis, sem rolagem horizontal da página.

---

### User Story 4 - Post do painel vinculado às métricas reais (Priority: P4)

Quem move um card do painel de marketing para "Publicado" informa o link do post publicado. Com o link, a rotina casa o export de conteúdo da Meta com o card certo e o relatório passa a falar dos posts pelo nome que o time usa (o título do card), além de avaliar as metas de frequência com as métricas reais. Sem link, a rotina tenta casar por data de publicação e plataforma; se a correspondência for ambígua, o post aparece como "não vinculado" em vez de ser atribuído errado.

**Why this priority**: fecha o ciclo planejamento → publicação → resultado dentro do ERP. Depende de o time alimentar o painel (ver Assumptions) e por isso vem depois do que funciona só com os exports.

**Independent Test**: publicar um card com link, rodar com o export de conteúdo correspondente e verificar que as métricas aparecem no card e no relatório com o título do card; repetir com um card sem link e dois posts na mesma data e verificar que o relatório mostra "não vinculado" para ambos.

**Acceptance Scenarios**:

1. **Given** um card publicado com link e o export de conteúdo contendo esse link, **When** a rodada executa, **Then** as métricas do post ficam vinculadas ao card e o relatório mostra o título do card.
2. **Given** um card publicado sem link, com um único post da mesma plataforma publicado no mesmo dia no export, **When** a rodada executa, **Then** o vínculo é feito por data e plataforma e marcado como "vínculo por data".
3. **Given** um card sem link e dois posts na mesma data e plataforma, **When** a rodada executa, **Then** nenhum vínculo é feito e ambos aparecem como "não vinculado — informe o link no card".
4. **Given** uma meta de frequência está atrasada na semana, **When** o relatório é montado, **Then** a meta aparece no bloco de frequência com o atraso em dias.

---

### User Story 5 - De qual campanha veio o lead e o evento (Priority: P5)

O CRM de vendas exporta os leads com origem e parâmetros de campanha (utm). A importação desse export, que o ERP já faz, passa a guardar esses campos no cliente. Com isso o relatório e a tela mostram, por campanha, quantos leads entraram, quantos viraram evento e quanto custou cada lead e cada evento fechado — e o custo de aquisição do mês (gasto de anúncios ÷ clientes novos).

**Why this priority**: é o que transforma "gastamos X" em "gastamos X e rendeu Y". Depende da qualidade do preenchimento das utms nas campanhas e da importação periódica do CRM, que são hábitos externos à feature.

**Independent Test**: importar um export do CRM com utm_campaign preenchido, rodar com o export de campanhas de mesmo nome e verificar que a tabela de campanhas mostra leads e eventos por campanha e o relatório traz o custo por lead; importar um export sem utms e verificar que a seção aparece como "sem atribuição disponível".

**Acceptance Scenarios**:

1. **Given** clientes importados com utm_campaign igual ao nome de uma campanha do export, **When** a rodada executa, **Then** a campanha mostra leads e eventos fechados atribuídos e o custo por lead.
2. **Given** nenhum cliente do período tem utm, **When** a rodada executa, **Then** o relatório informa "atribuição indisponível — utms não preenchidas no CRM" e o restante segue.
3. **Given** o mês corrente tem gasto de anúncios e clientes novos, **When** o relatório é montado, **Then** traz o custo de aquisição do mês (gasto ÷ clientes novos) com os dois números de base visíveis.

---

### Edge Cases

- Export com números no formato brasileiro ("1.234,56") ou americano ("1,234.56"): a leitura precisa reconhecer os dois sem trocar milhar por decimal; em dúvida, rejeita o arquivo e explica.
- Export de semana em curso (período parcial): os dias presentes são guardados; dias já guardados por um export anterior são substituídos pelo valor mais recente, nunca somados.
- Campanha renomeada na plataforma: passa a ser outra linha a partir da data da troca; o relatório destaca campanhas novas na semana.
- Arquivo vazio ou só com cabeçalho: listado como "sem linhas".
- Dois arquivos diferentes cobrindo a mesma plataforma e período com valores diferentes: vale o mais recente e o relatório registra que houve substituição.
- Post apagado do Instagram depois de medido: as métricas guardadas permanecem; o relatório não tenta remedir.
- Gasto Extra gerado pela rotina rejeitado pelo financeiro: a rotina não o recria na próxima rodada (o mês continua coberto) e o relatório menciona a rejeição uma vez — achados repetidos entre rodadas (mesmo código e mesma chave) são suprimidos depois da primeira vez, como no auditor financeiro.
- Gasto gerado sem comprovante: aparece no relatório como "aguardando fatura do cartão" até alguém anexar; a aprovação continua sendo decisão humana.
- Titular do cartão muda (por exemplo, passa a ser cartão da empresa): a rotina continua registrando o gasto; trocar o destinatário do reembolso é ajuste de configuração, não de código.
- Máquina do dono fora do ar por mais de uma semana: a rodada seguinte cobre toda a janela desde a última rodada enviada e diz isso no relatório.
- Segredos (credenciais de acesso, dados de banco) nunca aparecem no relatório, na tela ou em arquivos de saída.

## Requirements *(mandatory)*

### Functional Requirements

**Entrada e reconhecimento**

- **FR-001**: O sistema MUST ler todos os arquivos de uma pasta de entrada configurável e classificar cada um como: insights de conteúdo da Meta, insights da conta da Meta, campanhas do Meta Ads, campanhas do Google Ads, ou "não reconhecido".
- **FR-002**: O reconhecimento MUST tolerar variações de idioma e ordem de colunas por meio de um mapa de colunas configurável sem alteração de código, e MUST rejeitar (com motivo) qualquer arquivo cujas colunas essenciais não sejam encontradas — nunca preencher um número ausente com suposição.
- **FR-003**: O sistema MUST interpretar corretamente valores numéricos nos formatos brasileiro e americano e datas nos formatos usados pelas plataformas; ambiguidade insanável rejeita o arquivo.
- **FR-004**: Cada arquivo lido MUST ficar registrado com nome, impressão digital do conteúdo, tipo reconhecido, período coberto e resultado (aceito/rejeitado + motivo), e um arquivo com a mesma impressão digital MUST ser ignorado em rodadas seguintes.
- **FR-005**: Arquivos processados MUST ser movidos da pasta de entrada para uma pasta de processados (organizada por rodada), para o dono enxergar o que já foi lido.

**Histórico de métricas**

- **FR-006**: O sistema MUST guardar métricas por post e por data de medição (plataforma, identificador do post na plataforma, link quando houver, data de publicação, alcance, curtidas, comentários, salvamentos, compartilhamentos e demais métricas disponíveis). Os exports de conteúdo trazem totais acumulados do post até a data do export, então cada arquivo vira uma **fotografia** datada; a unicidade é plataforma + post + data da fotografia, e a evolução semanal é a diferença entre fotografias.
- **FR-007**: O sistema MUST guardar métricas por campanha e por período medido (plataforma, identificador e nome da campanha, gasto, impressões, cliques, resultados/conversões, moeda) com unicidade por plataforma + campanha + início + fim do período. A orientação ao operador é exportar **com detalhamento por dia**; linhas agregadas de vários dias são aceitas, mas quando coexistem com linhas diárias das mesmas datas o sistema MUST usar só as diárias no cálculo de gasto e registrar um achado de sobreposição.
- **FR-008**: O sistema MUST guardar métricas da conta por dia (seguidores, alcance da conta) por plataforma.
- **FR-009**: Reprocessar um período MUST substituir os valores daquele dia, nunca somar.

**Cruzamentos com o ERP**

- **FR-010**: O card de postagem do painel de marketing MUST ganhar um campo opcional "link do post publicado"; ao mover o card para "Publicado" o sistema MUST pedir o link (permitindo seguir sem ele).
- **FR-011**: A rotina MUST vincular métricas de post ao card pelo link; na ausência de link, por data de publicação + plataforma quando houver exatamente um candidato; caso contrário MUST marcar como "não vinculado" com a instrução de preencher o link.
- **FR-012**: A rotina MUST reportar as metas de frequência atrasadas no fechamento da semana, reutilizando o cálculo existente das metas (sem segunda implementação).
- **FR-013**: A importação do export do CRM de vendas MUST passar a guardar no cliente a origem do lead e os parâmetros utm (source, medium, campaign) quando presentes, sem alterar o comportamento atual para exports que não os tragam.

**Gasto de anúncios e reembolso**

- **FR-014**: Ao fim da rodada, para cada plataforma de anúncios com gasto no **mês civil** corrente (e no mês anterior, enquanto a rodada ainda vir dias dele), o sistema MUST manter um Gasto Extra de categoria Marketing por plataforma e mês, com desembolso por reembolso ao usuário configurado como titular do cartão, valor igual ao gasto acumulado do mês segundo a plataforma, data de competência igual ao último dia do mês, **status inicial pendente** (aprovação humana pelo financeiro, como qualquer Gasto Extra), **sem comprovante** (a fatura do cartão é anexada pelo financeiro antes da aprovação; o relatório lembra disso) e **reembolso com vencimento no dia 10** do mês seguinte à competência (decisão do dono, 2026-08-20). Enquanto o gasto estiver pendente, rodadas seguintes atualizam valor e detalhe por campanha; depois de aprovado ou rejeitado ele é congelado e qualquer diferença posterior vira achado (FR-017).
- **FR-015**: Cada Gasto Extra criado pela rotina MUST carregar o detalhe por campanha (nome, plataforma, valor) e a identificação da rodada e do(s) arquivo(s) de origem, visíveis ao abrir o gasto no ERP.
- **FR-016**: A criação MUST ser idempotente por plataforma + mês civil: repetir a rodada, reenviar o arquivo ou rodar em catch-up não cria gasto em duplicidade.
- **FR-017**: Se já existir gasto de Marketing cobrindo o mesmo mês e plataforma — manual (categoria Marketing, competência no mês e nome da plataforma na descrição) ou da rotina já aprovado/rejeitado — o sistema MUST NOT criar outro e MUST registrar um achado quando o valor divergir do reportado pela plataforma em mais de R$ 0,01.
- **FR-018**: Gasto em moeda diferente de real MUST ser recusado para criação de reembolso e reportado.
- **FR-019**: A escrita da rotina no ERP MUST se limitar à criação de Gasto Extra de Marketing e de seus detalhes por campanha, por um canal exclusivo protegido por credencial própria, desligável por configuração — qualquer outra escrita é proibida.

**Relatório e entrega**

- **FR-020**: A rotina MUST produzir um relatório em português com, nesta ordem: manchete da semana (leads por campanha e custo por lead); leads e eventos por campanha (quando houver atribuição) e custo de aquisição do mês; gasto por plataforma e por campanha com custo por clique; posts publicados × metas de frequência; 3 melhores e 3 piores posts por alcance e por engajamento; seguidores (variação na semana); conferência financeira (reportado × lançado no ERP); o que ficou sem dado; arquivos rejeitados.
- **FR-021**: O relatório MUST trazer gráficos legíveis em cliente de e-mail (sem depender de script): série semanal de alcance e seguidores, barras de gasto por campanha e funil gasto → cliques → leads → fechados.
- **FR-022**: O relatório MUST ser enviado por e-mail ao dono (destinatários configuráveis entre usuários internos ativos) toda segunda-feira; se o envio falhar, o arquivo do relatório MUST ser entregue ao operador com aviso explícito.
- **FR-023**: A rotina MUST rodar sem intervenção toda segunda-feira cedo e MUST executar em catch-up quando a máquina estiver desligada no horário, cobrindo a janela desde a última rodada enviada.
- **FR-024**: O relatório MUST declarar a janela coberta e o número da rodada, e MUST dizer explicitamente quando a janela for maior que uma semana.

**Tela no ERP**

- **FR-025**: O ERP MUST oferecer a tela "Marketing → Desempenho", visível e acessível apenas aos papéis que já acessam o painel de marketing, com: gráficos de série semanal (alcance, seguidores), gasto por campanha, funil por campanha, tabela de posts com métricas e vínculo ao card, tabela de campanhas, e lista das rodadas (data, janela, arquivos aceitos/rejeitados).
- **FR-026**: A tela MUST permitir escolher o período (últimas 4, 12, 26 semanas ou intervalo livre) e MUST ter estado vazio orientando onde salvar os exports e quando a rotina roda.
- **FR-027**: A tela MUST ser utilizável no celular (sem rolagem horizontal da página; gráficos e tabelas rolam dentro do próprio bloco quando necessário).

**Operação e segurança**

- **FR-028**: Nenhum segredo (credenciais, endereços de banco) MUST aparecer em relatório, tela, arquivo de saída ou resumo de rodada.
- **FR-029**: A rotina MUST NOT enviar nenhuma comunicação além do relatório ao(s) destinatário(s) configurado(s) e MUST NOT disparar integrações externas (agenda, mensagens, pagamentos).
- **FR-030**: Toda rodada MUST deixar um registro local (janela, arquivos, métricas gravadas, gastos criados, achados, e-mail enviado) que permita refazer ou auditar a rodada.

### Key Entities

- **Arquivo de entrada**: um export salvo na pasta; tem nome, impressão digital, tipo reconhecido, período coberto, resultado da leitura e a rodada que o processou.
- **Rodada**: uma execução da rotina; tem janela (início/fim), data de execução, arquivos lidos, contagens do que foi gravado, achados e status do envio do relatório.
- **Métrica de post por dia**: medição de um post numa plataforma num dia; liga-se opcionalmente a um card do painel de marketing.
- **Métrica de campanha por dia**: medição de uma campanha de anúncios numa plataforma num dia (gasto, impressões, cliques, resultados, moeda).
- **Métrica da conta por dia**: seguidores e alcance da conta por plataforma e dia.
- **Card de postagem (existente)**: ganha o link do post publicado.
- **Cliente (existente)**: ganha origem do lead e utms vindos do CRM.
- **Gasto Extra (existente)**: ganha a marca de origem "auditor de marketing" e o detalhe por campanha (linhas filhas com plataforma, campanha e valor).
- **Achado**: divergência ou alerta de uma rodada (valor lançado × reportado, meta atrasada, arquivo rejeitado, post não vinculado), com severidade e texto em português.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Toda segunda-feira o dono recebe, sem pedir, um relatório com todos os blocos obrigatórios preenchidos ou explicitamente marcados como "sem dado" — em 4 semanas consecutivas de operação, zero relatórios perdidos (contando o catch-up).
- **SC-002**: O esforço humano semanal para alimentar a mensuração cai para no máximo 10 minutos (exportar e salvar até 4 arquivos); nenhuma digitação de número é necessária.
- **SC-003**: 100 % do gasto de anúncios reportado pelas plataformas no período aparece no ERP como gasto de Marketing para reembolso, com zero duplicidades em 4 semanas de operação e com o detalhe por campanha consultável em cada gasto.
- **SC-004**: Nenhum número inventado: todo arquivo não reconhecido ou incompleto aparece no relatório pelo nome e motivo (verificável plantando um arquivo inválido e um arquivo faltante numa rodada de teste).
- **SC-005**: Com o link preenchido no card, 100 % dos posts publicados na semana aparecem no relatório com o título do card; sem link, a taxa de vínculo automático por data é reportada e nenhum vínculo ambíguo é feito.
- **SC-006**: A tela de Desempenho mostra 12 semanas de histórico em até 3 segundos percebidos e é legível no celular sem rolagem horizontal da página.
- **SC-007**: O dono consegue responder, só com o relatório, às três perguntas: "quanto gastamos e em quê", "o que rendeu (alcance, leads, eventos) por campanha" e "o que ficou atrasado ou sem medir" — validado em leitura do primeiro relatório real.

## Clarifications

### Session 2026-08-20

- Q: O Gasto Extra de anúncios criado pela rotina nasce como, e quando é o reembolso? → A: Pendente (aprovação humana), reembolso com vencimento no dia 10.
- Q: Qual é o número um do marketing (manchete do relatório)? → A: Leads para o comercial; alcance/seguidores em segundo plano.
- Decisão de planejamento (2026-08-20): o período do reembolso automático é o **mês civil** (um Gasto Extra por plataforma e mês, atualizado enquanto pendente) — unidade da fatura do cartão e do vencimento dia 10; e os gráficos do e-mail são barras em HTML/CSS porque clientes de e-mail (Gmail) não renderizam SVG embutido — os gráficos SVG ficam na tela do ERP.

## Assumptions

- O dono é o titular do cartão e o destinatário do reembolso; trocar o titular é configuração.
- O relatório vai apenas ao dono no início; destinatários adicionais (pessoas do marketing) são configuráveis entre usuários internos ativos, como no auditor financeiro.
- **O número um do marketing é "leads para o comercial"** (decisão do dono, 2026-08-20): a manchete da semana é leads por campanha e custo por lead; quando não houver atribuição disponível na semana, a manchete cai para **alcance total da semana** e diz por que (utms/import do CRM ausentes). Alcance e seguidores vêm depois dos leads na ordem dos blocos.
- O painel de marketing do ERP precisa ser alimentado pelo time para as histórias 4 e 5 terem valor: o espelho de produção de 20/08/2026 tinha **zero** postagens cadastradas. As histórias 1, 2 e 3 funcionam só com os exports; se o painel seguir vazio, o relatório diz quantos posts do export não têm card correspondente — isso é um achado, não um erro.
- Os exports seguem os formatos padrão atuais da Meta (Business Suite e Gerenciador de Anúncios) e do Google Ads em português do Brasil; mudanças de formato são absorvidas pelo mapa de colunas configurável, não por código.
- O export do CRM de vendas continua sendo importado periodicamente no ERP pelo processo já existente; a atribuição depende de as campanhas serem publicadas com utms preenchidas.
- A moeda de todas as contas de anúncios é o real.
- A pasta de entrada mora na máquina que executa a rotina; backup dos arquivos processados é responsabilidade da pasta de processados + histórico no ERP.
- Fora de escopo nesta feature: leitura automática de e-mail, integração direta com as APIs da Meta/Google, upload de arquivos pela interface do ERP, métricas de WhatsApp e da loja virtual (podem entrar como indicador de resultado numa fase seguinte).
