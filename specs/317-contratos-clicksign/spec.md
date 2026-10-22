# Feature 317 — O contrato da ClickSign se liga sozinho à venda, a situação fica clara e a comercial cobra em um clique

**Branch**: `317-contratos-clicksign` (da `main` em `5781993c`, worktree `C:\tmp\mp317`) · **Created**: 2026-10-22 ·
**Status**: Rascunho · **Migration**: uma, aditiva (documentos da ClickSign, caixa de entrada do aviso, registro de
cobrança, segredo do aviso) · **Nível**: 1 (feature) — integração externa nova, endpoint e tela novos, três domínios
(agenda/venda, formulários, Home) — constituição, Princípio VI

**Input**: pedido do dono: "Preciso que verifique se há a possibilidade de anexar ou vincular os contratos do ClickSign
com os clientes e deixar isso de forma mais clara e automatizar de forma rápida e sem ação humana. No máximo para
verificar se de fato é esse, está correto. E também ficar claro, tipo assim, precisa cobrar esse contrato, esse aqui foi
assinado, não precisa cobrar mais. […] Sabe a lógica de cobrança de valor financeiro? Também ter um botãozinho para
cobrar contrato. E aí, uma mensagem explicando: o ClickSign te manda uma mensagem pelo WhatsApp, numa conversa com o
ClickSign, é só clicar lá e assinar." (22/10/2026). Plano aprovado no mesmo dia ("autorizo"), seguindo a esteira do
Spec Kit.

## O pedido, nas palavras do dono *(obrigatório)*

O pedido está acima. O sintoma, como a equipe vive hoje:

- A cliente fecha no WhatsApp/Kommo e preenche o formulário da Manto (`/f/pre-contrato` ou `/f/corporativo`), que só
  manda as respostas ao WhatsApp da Manto. **A comercial transcreve** essas respostas para um "Fluxo com formulário" da
  ClickSign ("Contratos Monta", "Prime Dreams Corporativo" e as variantes por e-mail), que gera o documento e o manda à
  cliente por uma conversa da ClickSign no WhatsApp.
- O sistema não sabe que o contrato existe. Às vezes alguém baixa o PDF e anexa no evento à mão, e só o Superadmin pode
  marcar "assinado": no espelho de 30/09, **7 de 60** anexos estavam marcados, e o histórico grava "Adicionou contrato
  assinado" mesmo sem a marca. Ninguém sabe, olhando o sistema, quem precisa ser cobrado.
- O contrato tem **5 a 6 dias** para ser assinado e, se vencer, a ClickSign o cancela sozinha. Na conta há ~13 páginas
  de cancelados para ~13 de finalizados: parte é reenvio duplicado, parte é contrato que venceu sem ninguém perceber.

## Clarifications

### Decisões do dono (22/10/2026, palavras dele nas respostas; não se reabrem)

1. **"Cobrar contrato" só copia a mensagem**, como a cobrança de valor: a comercial cola no WhatsApp/Kommo da cliente.
   Não dispara reenvio pela ClickSign (o lembrete por WhatsApp da ClickSign é cobrado à parte). O sistema registra quem
   cobrou e quando.
2. **O botão fica no menu ⋯ do evento e em cada linha do painel "Contratos" da Home.**
3. **Cobram contrato e confirmam o "é esse mesmo?": COMERCIAL e SUPERADMIN.** O FINANCEIRO vê a situação, mas não
   cobra nem confirma.
4. **Gerar o contrato pela ClickSign a partir do formulário fica para uma feature própria**, depois desta.

### Fatos conferidos na conta da ClickSign (22/10/2026, só leitura)

- Conta **PRIME DREAMS LTDA**, plano **Plus Automação 100** (WhatsApp e fluxos com formulário incluídos). Em
  Configurações › API já existe um token de acesso chamado "Plataforma Manto", nunca usado; nenhum aviso automático
  (webhook) cadastrado.
- Todo documento de cliente leva no nome a **data do evento**, o **WhatsApp de quem assina** e o **tema** (festa:
  `25102026 + (11) 98492-5407 + Hot Wheels.pdf`; corporativo: `07112026 + Clube Atlético São Paulo + (11) 94370-4338.pdf`).
  A data é digitada à mão: aparecem `DD-MM-AAAA` (até julho), `DDMMAAAA` e `DMMAAAA` (`4122026`). Reenvio leva `(1)`.
- Contrato de **artista** ("…_CONTRATO DE PRESTAÇÃO DE SERVIÇOS ARTÍSTICOS_Cidade") e avulsos ("Declaração Estágio…")
  convivem na mesma conta.
- Cada documento tem um signatário, avisado e autenticado pelo WhatsApp (nos fluxos "e-mail", pelo e-mail), com prazo
  de 5–6 dias.

### Session 2026-10-22 (`/speckit-specify`) — leituras fixadas por esta spec, não palavras do dono

Premissas contestáveis no `/speckit-clarify`; o dono só precisa dizer se discorda.

1. **A unidade do contrato é a venda**: o evento avulso ou o principal do grupo, como a cobrança de valor (299). Um
   contrato ligado a qualquer dia do grupo vale para a venda inteira.
2. **Quais vendas entram**: as da cobrança de valor **mais cortesia/permuta** (decidido no clarify) — fora cancelado,
   ensaio, compromisso interno (🟧/🟠) e loja virtual — com evento a partir de **01/06/2026**.
3. **Documento vigente**: entre os contratos de cliente ligados à mesma venda, vale o **mais recente**. Um reenvio
   assinado não fica "vencido" porque a cópia anterior foi cancelada depois; um contrato novo (remarcação) substitui o
   antigo.
4. **Assinado à mão continua valendo**: venda sem contrato da ClickSign, mas com anexo marcado "assinado" pelo
   Superadmin (DocuSign, papel), aparece "Assinado (marcado à mão)". A marca manual continua só do Superadmin.
5. **Régua de cor** (a mesma linguagem da Home): vermelho quando o contrato vence hoje ou amanhã, ou o evento é em até
   7 dias; amarelo quando vence em 2–3 dias, ou o evento é em 8–30 dias; cinza no resto. Vale a pior das duas
   (confirmada no clarify).

### Session 2026-10-22 (`/speckit-clarify`)

- Q: Venda de cortesia ou permuta também precisa de contrato assinado? → A: Entra — aparece em "Contratos" e pode ser
  cobrada como qualquer venda.
- Q: No grupo "Venda sem contrato" da Home, quais vendas aparecem? → A: Só as com evento nos próximos 30 dias; as mais
  distantes ficam na página do evento.
- Q: Quando a linha de contrato aguardando assinatura fica vermelha? → A: Prazo vence hoje/amanhã ou evento em até 7
  dias; amarelo com prazo em 2–3 dias ou evento em 8–30; cinza no resto.

## Cenários e Verificação *(obrigatório)*

### História 1 — O contrato aparece ligado à venda certa, sem ninguém fazer nada (Prioridade: P1)

A comercial gera o contrato na ClickSign como hoje. Minutos depois, a página do evento mostra "Aguardando assinatura —
vence em 5 dias" com o nome do documento; quando a cliente assina, passa a "Assinado em 22/10", e o PDF assinado já
está nos anexos do evento. Ninguém colou link, subiu arquivo nem marcou nada.

**Por que esta prioridade**: é o pedido central ("automatizar sem ação humana") e a base de todo o resto: sem o vínculo
certo, a cobrança cobra a pessoa errada.

**Verificação**: cenários 1–8 e 12–15 do `verify_317.py` — leitura do nome com as variações reais, vínculo único,
desempate pelo tema, telefone de outra pessoa, venda cancelada, grupo, documento vigente, PDF anexado, aviso repetido.

**Cenários de aceite**:

1. **Dado** uma venda em 25/10 cuja cliente tem o WhatsApp (11) 98492-5407, **Quando** a ClickSign avisa um documento
   `25102026 + (11) 98492-5407 + Hot Wheels.pdf`, **Então** o documento fica ligado a essa venda sozinho e a situação
   vira "Aguardando assinatura" com o prazo da ClickSign.
2. **Dado** o mesmo documento ligado, **Quando** a cliente assina, **Então** a situação vira "Assinado em DD/MM", o PDF
   assinado entra nos anexos do principal marcado como assinado, com autor "ClickSign (automático)", e a venda sai das
   listas de cobrança.
3. **Dado** duas vendas na mesma data com o mesmo telefone, **Quando** o tema do documento bate com só uma delas,
   **Então** liga nessa; **se** não bater com nenhuma, o documento vai para "A conferir" e não liga em nenhuma.
4. **Dado** um documento cuja data e telefone não batem com nenhuma venda viva, **Quando** chega, **Então** vai para
   "A conferir" com as vendas mais parecidas como sugestão (mesmo telefone em até 3 dias, ou mesma data com outro
   telefone da cliente), e nunca liga sozinho.
5. **Dado** um contrato de artista ou um documento avulso, **Quando** chega, **Então** é guardado como "não é de
   cliente" e não aparece em nenhuma lista de venda.
6. **Dado** uma venda cancelada, **Quando** um documento bate com ela, **Então** ele não liga (vai para "A conferir",
   com o motivo "a venda está cancelada").

---

### História 2 — A comercial vê quem precisa ser cobrado e cobra em um clique (Prioridade: P1)

Na Home, o painel "Contratos" mostra, por cor, as vendas cujo contrato está aguardando assinatura, as que venceram sem
assinatura, as vendas sem contrato e os documentos a conferir. Em cada linha de "Para cobrar", o botão "Cobrar
contrato" copia a mensagem pronta; a linha passa a mostrar "Cobrado por Fulana em 22/10, 14:05". O mesmo botão está no
menu ⋯ do evento.

**Por que esta prioridade**: é o "precisa cobrar × não precisa cobrar mais" que o dono pediu, e o botão é o que tira o
trabalho da comercial.

**Verificação**: cenários 9–11 e 16–17 do `verify_317.py` — situação e listas, mensagem pelo canal certo, registro da
cobrança, travas do botão, RBAC.

**Cenários de aceite**:

1. **Dado** uma venda com contrato aguardando assinatura, **Quando** a comercial toca em "Cobrar contrato", **Então** a
   mensagem é copiada (saudação pela hora, tema e data da festa, e a explicação de que a ClickSign mandou uma conversa
   no WhatsApp e é só abrir, tocar no link e assinar) e a cobrança fica registrada com quem e quando.
2. **Dado** um contrato cujo signatário recebe pelo e-mail, **Quando** a comercial cobra, **Então** a mensagem fala do
   e-mail da ClickSign, não do WhatsApp.
3. **Dado** uma venda assinada, vencida, sem contrato, cancelada ou um dia do grupo que não é o principal, **Quando** a
   comercial abre o menu, **Então** "Cobrar contrato" aparece desativado com o motivo ("Contrato já assinado", "O
   contrato venceu sem assinatura. Gere um novo na ClickSign.", "Nenhum contrato na ClickSign para esta venda", "A
   cobrança deste grupo está no evento principal").
4. **Dado** o FINANCEIRO, **Quando** abre o evento ou a Home, **Então** vê a situação do contrato, mas não o botão de
   cobrar nem o de confirmar vínculo; um pedido direto à API devolve 403.

---

### História 3 — "É esse mesmo?": a conferência do que o sistema não teve certeza (Prioridade: P2)

Em "A conferir", cada documento mostra o nome, a data, o telefone e a sugestão de venda. A comercial toca em **Ligar**
(ou escolhe outra venda) ou em **Não é deste evento**. O que foi ligado sozinho e estava errado pode ser **desligado**
na página do evento e não volta a se ligar sozinho na mesma venda.

**Por que esta prioridade**: é o "no máximo para verificar" do dono; sem ela, um vínculo duvidoso ficaria parado.

**Verificação**: cenários 18–20 do `verify_317.py`.

**Cenários de aceite**:

1. **Dado** um documento a conferir com sugestão, **Quando** a comercial toca em "Ligar", **Então** ele passa a valer
   para a venda (origem "manual", com quem e quando) e sai da lista.
2. **Dado** um documento ligado sozinho à venda errada, **Quando** a comercial toca em "Desligar", **Então** a venda
   volta à situação anterior, o documento volta para "A conferir" e o sistema não o religa sozinho nessa venda.
3. **Dado** um documento a conferir, **Quando** a comercial toca em "Não é de nenhuma venda", **Então** ele sai da lista
   para sempre (confirmação curta antes).

---

### História 4 — O que já existe desde junho entra de uma vez (Prioridade: P2)

Um comando de manutenção puxa da ClickSign os documentos criados desde 01/06/2026, liga cada um à venda pela mesma regra,
anexa o PDF assinado que faltar e mostra, antes de gravar, quantos ligaria, quantos ficariam a conferir e quantos
anexos antigos passariam a "assinado".

**Por que esta prioridade**: sem ele, a lista nasce com dezenas de vendas falsamente "sem contrato" e a equipe perde a
confiança no painel no primeiro dia.

**Verificação**: cenário 21 do `verify_317.py` (simulação sem gravar, depois gravação, depois repetição sem efeito).

**Cenários de aceite**:

1. **Dado** o comando sem `--aplicar`, **Quando** roda, **Então** só conta e lista, e nada é gravado.
2. **Dado** o comando com `--aplicar` rodado duas vezes, **Quando** termina a segunda, **Então** nada muda (idempotente).

---

### História 5 — O aviso perdido não deixa contrato "a cobrar" para sempre (Prioridade: P3)

Se o sistema estiver fora do ar quando a ClickSign avisar (deploy, queda), uma conferência leve e periódica busca o que
mudou desde a última e acerta a situação, sem ninguém pedir.

**Por que esta prioridade**: a ClickSign não documenta reenvio do aviso; sem isso, a assinatura feita durante um deploy
nunca chegaria.

**Verificação**: cenário 22 do `verify_317.py`.

**Cenários de aceite**:

1. **Dado** um documento assinado cujo aviso não chegou, **Quando** a conferência periódica roda, **Então** a situação
   vira "Assinado" e o PDF é anexado, como se o aviso tivesse chegado.

### Casos de borda

- Data do nome com erro de digitação, ano trocado ou sem zero à esquerda: ler o que der; data que não forma dia válido →
  "A conferir", nunca descartado.
- Número americano (+1) ou telefone fora do padrão no nome: não liga sozinho → "A conferir".
- Dois documentos da mesma venda (reenvio `(1)`): vale o mais recente; o cancelado mais antigo não derruba "Assinado".
- Cliente recusa assinar na ClickSign: situação "Recusado pela cliente" (vermelho, sai de "Para cobrar", fica em "Venceu
  ou foi recusado").
- Aviso repetido, fora de ordem ou de documento desconhecido: processado uma vez só; o sistema confirma na ClickSign
  antes de mudar a situação (o conteúdo do aviso nunca decide sozinho).
- Aviso com assinatura de segurança errada: recusado sem efeito.
- Venda cancelada depois de ligada: o vínculo fica (histórico), a venda sai das listas como em toda a casa (312).
- Venda excluída: o documento volta para "A conferir".
- Venda em grupo que troca de principal: o vínculo segue a venda (passagem de grupo).
- Integração desligada (sem token) ou ClickSign fora do ar: a situação cai para o que existe hoje (anexos), a Home mostra
  "Integração com a ClickSign desligada" só ao Superadmin, e nada quebra.
- Duas pessoas ligando, desligando ou descartando o mesmo documento ao mesmo tempo: vale a primeira; a segunda recebe
  "este contrato acabou de ser alterado" e a tela se atualiza.
- PDF assinado indisponível no momento do aviso: a situação vira "Assinado" mesmo assim; o anexo é tentado de novo na
  conferência seguinte.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Vínculo**

- **FR-001**: O sistema DEVE receber da ClickSign, sem ação humana, cada documento criado, assinado, finalizado,
  cancelado, vencido ou recusado na conta, e guardar a identificação dele, nome, situação, prazo, datas, telefone/e-mail
  e canal do signatário.
- **FR-002**: O sistema DEVE classificar cada documento como **de cliente** (nome com data e telefone, festa ou
  corporativo), **de artista** ou **outro**; só o de cliente liga sozinho a uma venda. O "outro" com data legível (ex.:
  corporativo só com razão social) vai para "A conferir" com sugestões pela data; artista e "outro" sem data ficam fora
  das listas.
- **FR-003**: O sistema DEVE ler do nome a data (`DD-MM-AAAA`, `DDMMAAAA`, `DMMAAAA`), o telefone `(DD) NNNNN-NNNN` e o
  tema ou razão social, tolerando o sufixo `(1)` e espaços.
- **FR-004**: O sistema DEVE ligar sozinho o documento de cliente à venda viva (principal ou avulso) com evento na data
  lida e telefone igual ao da cliente do evento, de uma contratante do evento ou do formulário ligado; empate se resolve
  pelo tema; sem candidato único, o documento vai para "A conferir" com sugestões, e nunca liga sozinho.
- **FR-005**: O sistema NUNCA DEVE ligar sozinho a venda cancelada, nem religar sozinho um documento à venda de onde ele
  foi desligado ou descartado.
- **FR-006**: COMERCIAL e SUPERADMIN DEVEM poder ligar um documento a uma venda, desligá-lo e descartá-lo ("não é de
  nenhuma venda", com confirmação), com registro de quem e quando.

**Situação**

- **FR-007**: O sistema DEVE mostrar a situação do contrato da venda na página do evento (aba Comercial e chip do Resumo):
  Assinado em DD/MM · Assinado (marcado à mão) · Aguardando assinatura — vence em N dias · Venceu sem assinatura ·
  Recusado pela cliente · Sem contrato na ClickSign; e a faixa "Achamos um contrato que parece desta venda" quando houver
  sugestão a conferir.
- **FR-008**: A situação DEVE vir do documento vigente da venda (o mais recente ligado), julgada pelo principal do grupo,
  e cair para a marca manual do Superadmin quando não houver documento da ClickSign.
- **FR-009**: Ao saber que o contrato foi assinado, o sistema DEVE anexar o PDF assinado ao principal da venda, marcado
  como assinado, com autor "ClickSign (automático)", sem duplicar o que já estiver anexado do mesmo documento.

**Home e cobrança**

- **FR-010**: A Home DEVE ter o painel "Contratos" (depois de Cobranças) com os grupos "Para cobrar", "Venceu ou foi
  recusado", "Venda sem contrato" (só evento nos próximos 30 dias), "A conferir" e, recolhido, "Já aconteceu sem
  contrato assinado"; cada linha com cliente, data do evento, prazo, cor pela régua da Premissa 5 e a última cobrança.
  Os três primeiros grupos levam só evento de hoje em diante; evento que já passou (desde o corte) sem contrato assinado,
  em qualquer situação, vai para "Já aconteceu". Cor de "Venda sem contrato" pela distância do evento (vermelho até 7
  dias, amarelo 8–30); "Venceu ou foi recusado" é sempre vermelho.
- **FR-019**: A coluna "Contrato" da lista de vendas (`/vendas`) DEVE mostrar a mesma situação da página do evento,
  julgada pela venda (uma fonte só); com a integração desligada, continua como hoje.
- **FR-011**: "Cobrar contrato" DEVE copiar a mensagem pronta, escolhida pelo canal do signatário (WhatsApp ou e-mail),
  com saudação pela hora, tema e data da festa, e DEVE registrar quem cobrou e quando.
- **FR-012**: "Cobrar contrato" DEVE ficar ativo só no principal ou avulso com contrato aguardando assinatura, e
  desativado com o motivo nos outros casos (FR-007).
- **FR-013**: O botão DEVE estar no menu ⋯ do evento e em cada linha de "Para cobrar" na Home.

**Retroativo e conferência**

- **FR-014**: Um comando de manutenção DEVE trazer os documentos desde 01/06/2026, simular sem gravar por padrão e gravar
  só com `--aplicar`, de forma idempotente.
- **FR-015**: O sistema DEVE conferir periodicamente, com poucas consultas, o que mudou na ClickSign desde a última
  conferência, para cobrir aviso perdido.

**Segurança e operação**

- **FR-016**: O aviso da ClickSign DEVE ser aceito só com a assinatura de segurança correta, processado uma vez só e
  confirmado na ClickSign antes de mudar qualquer situação.
- **FR-017**: Nenhuma cópia local do banco (espelho, verify, script) DEVE falar com a ClickSign real sem liberação
  explícita; a credencial da ClickSign NUNCA DEVE ficar no banco.
- **FR-018**: Sem credencial configurada, a integração DEVE ficar desligada e avisar no log da subida, sem quebrar
  nenhuma tela.

### Entidades

- **Documento da ClickSign**: um documento da conta (identificação na ClickSign e do envelope, nome, tipo
  cliente/artista/outro, situação, prazo, criado/assinado/cancelado em, telefone/e-mail e canal do signatário, data,
  telefone e tema lidos do nome, venda ligada, origem do vínculo automático/manual, estado do vínculo
  ligado/a conferir/descartado, quem ligou/desligou e quando, anexo assinado gerado, última conferência).
- **Aviso recebido**: não é guardado. O aviso só dispara a sincronização com a ClickSign, que é idempotente (o mesmo
  documento nunca vira duas linhas nem dois anexos), então repetir ou perder um aviso não muda o resultado.
- **Cobrança de contrato**: cada "Cobrar contrato" (documento, venda, quem, quando).
- **Desvínculo**: par documento × venda que a comercial desligou ou recusou; o sistema não religa sozinho esse par.
- **Configuração**: segredo do aviso, revogável, e o marco da última conferência.

Modelos em `app/models.py`, migration à mão, aditiva.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/events/<id>` (bloco do contrato) e `GET /api/dashboard` (painel Contratos) — COMERCIAL, FINANCEIRO,
  SUPERADMIN (o mesmo `show_comercial` de hoje); `pode_cobrar` só para COMERCIAL e SUPERADMIN.
- `POST /api/contratos/<id>/cobranca` — COMERCIAL, SUPERADMIN.
- `POST /api/contratos/<id>/ligar`, `/desligar`, `/descartar` — COMERCIAL, SUPERADMIN.
- `POST /api/webhooks/clicksign` — sem sessão; vale só com a assinatura de segurança da ClickSign.
- Linhas novas na tabela de `docs/01` §4.3.

## Verificação (`verify_317.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/317-contratos-clicksign/verify_317.py`, contra `manto_local` (`DATABASE_URL` de `.local-db-url`,
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`), com a ClickSign trocada por um dublê e um disjuntor de rede que derruba
qualquer conexão de saída. Login só por `POST /api/auth/login`; escrita conferida por conexão separada; limpeza no
`finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | leitura do nome com as variações reais (DD-MM-AAAA, DDMMAAAA, DMMAAAA, `(1)`, corporativo) | FR-003 | não |
| 2 | classificação cliente × artista × outro | FR-002 | não |
| 3 | vínculo único por data + telefone da cliente / contratante / formulário | FR-004 | não |
| 4 | empate resolvido pelo tema; empate sem tema → a conferir | FR-004 | não |
| 5 | sem candidato → a conferir com sugestões; nunca liga | FR-004 | não |
| 6 | venda cancelada não liga | FR-005 | não |
| 7 | grupo: documento no satélite vale para a venda; situação pelo principal | FR-008 | não |
| 8 | vigente: reenvio assinado + original cancelado depois = assinado; remarcação substitui | FR-008 | não |
| 9 | situação na página do evento, nas listas da Home (cada grupo, cor, fronteira de data) e na coluna de `/vendas` | FR-007, FR-010, FR-019 | não |
| 10 | mensagem pelo canal (WhatsApp × e-mail) e registro da cobrança | FR-011 | não |
| 11 | botão desativado com o motivo certo (assinado, vencido, sem contrato, cancelado, satélite) | FR-012 | não |
| 12 | assinado → PDF anexado ao principal, marcado, autor automático, sem duplicar | FR-009 | não |
| 13 | aviso com assinatura de segurança errada | recusado, nada gravado | **sim** |
| 14 | aviso repetido / fora de ordem | processado uma vez; reconsulta decide | não |
| 15 | aviso cujo conteúdo diz "assinado" mas a ClickSign diz "em processo" | situação não muda | **sim** |
| 16 | FINANCEIRO tenta cobrar / ligar | 403 | **sim** |
| 17 | CASTING tenta ver o bloco do contrato | ausente / 403 | **sim** |
| 18 | ligar manual a partir de "A conferir" | FR-006 | não |
| 19 | desligar e não religar sozinho | FR-005, FR-006 | não |
| 20 | descartar | FR-006 | não |
| 21 | comando retroativo: simulação não grava; `--aplicar` duas vezes = idempotente | FR-014 | não |
| 22 | conferência periódica acerta aviso perdido | FR-015 | não |
| 23 | trava: nenhuma conexão de saída com a cópia local | FR-017 | não |
| 24 | sem credencial: integração desligada, telas respondem | FR-018 | não |
| 25 | rotas novas de escrita classificadas no `verify_312` (cancelado) | — | não |
| 26 | limpeza | registros descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela: Home (painel Contratos, com e sem itens, 375 px), página do evento (aba Comercial, chip do Resumo,
menu ⋯) como COMERCIAL e como FINANCEIRO; faixa "A conferir".

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Nos 30 dias depois da entrega, pelo menos 9 de cada 10 contratos de cliente criados na ClickSign ficam
  ligados à venda certa sem nenhum clique (contagem: documentos de cliente criados no período com vínculo de origem
  automática que nunca foram desligados ÷ todos os documentos de cliente do período).
- **SC-002**: Nenhum contrato fica ligado sozinho à venda errada sem que a tela mostre a divergência (data, telefone ou
  tema); todo desligamento fica registrado com quem e quando, e o número de desligamentos de vínculos automáticos nos 30
  dias é zero ou explicado um a um.
- **SC-003**: A assinatura aparece no sistema em até 5 minutos depois que a cliente assina, e no máximo até a conferência
  periódica seguinte quando o aviso se perder.
- **SC-004**: A comercial cobra um contrato a partir da Home em no máximo 2 toques, sem abrir o evento.
- **SC-005**: Depois do comando retroativo, toda venda desde 01/06/2026 com contrato na ClickSign mostra a situação real;
  nenhuma venda já assinada aparece em "Para cobrar".
- **SC-006**: Nenhuma mensagem nem consulta sai para a ClickSign a partir de uma cópia local do banco.

## Fora de escopo

- Gerar o contrato pela ClickSign a partir do formulário e do evento (feature própria, decisão 4).
- Reenvio ou lembrete pago pela ClickSign (decisão 1).
- Ligar contratos de artista ao banco de talentos.
- Abrir o WhatsApp direto no número da cliente (a mensagem é copiada, como a cobrança de valor).
- Mudar quem marca "assinado" à mão (continua só o Superadmin).
- Conciliação de PIX pelos e-mails dos bancos (feature 318, planejada em outra sessão).

## Docs a atualizar

`docs/01` (integração ClickSign, tabelas novas, endpoints, RBAC §4.3, env e trava, operação do comando e do aviso; corrige
as menções antigas em :203 e :638), `docs/02` (painel Contratos na Home, bloco do contrato no evento; corrige :2080),
`docs/03` (entrada no topo), `docs/04` (invariante: contrato é da venda, documento vigente, conteúdo do aviso nunca
decide sozinho), `docs/05` (dívidas novas; colunas `clicksign_*` inertes do `SiteSetting`).

## Premissas

- As cinco premissas da sessão `/speckit-specify` acima.
- O token "Plataforma Manto" que já existe na conta é o que vai para a produção; o dono o coloca no painel do Render.
- Os documentos dos fluxos com formulário são visíveis pela API da ClickSign com esse token — conferido no Portão 0 do
  `research.md` antes de fechar o plano; se não forem, o plano muda de fonte (e-mails da ClickSign) e a spec volta para
  revisão.
- O cadastro do aviso automático na ClickSign é feito pelo próprio sistema, sem o dono entrar no painel.
- Do signatário, a Manto guarda só nome, telefone, e-mail e canal de envio — o necessário para ligar e cobrar. CPF,
  endereço e IP que a ClickSign tem não são copiados (o PDF assinado anexado continua tendo o log da ClickSign, como hoje).
