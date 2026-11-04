# Feature 333 — Orçamento e formulário pela conversa, com o orçamento ligado à ficha

**Branch**: `333-crm-orcamento-na-conversa` (da `332-crm-avisos-no-celular`, fora da `main`: o dono adiou a
publicação) · **Created**: 2026-11-03 · **Status**: Rascunho · **Migration**: sim, aditiva (1 tabela nova e 1 coluna)
· **Nível**: 1 (feature)

**Input**: pedido do dono (03/11): "Começar a Fase 3". É a fatia 3a da Fase 3 do `docs/PLANO_CRM_PROPRIO.md`
("Costura com a Plataforma"), com as decisões do mesmo dia (Clarifications).

## O pedido, nas palavras do dono *(obrigatório)*

> "Começar a Fase 3" (03/11)

O plano diz que a Fase 3 termina quando "um orçamento de verdade vai da conversa à venda sem copiar e colar". Hoje o
vendedor gera o orçamento na calculadora, clica em "Copiar mensagem", cola no WhatsApp, baixa o PDF, anexa no WhatsApp
e, quando a cliente fecha, cria o evento e procura a ficha dela de novo. O orçamento não sabe de quem é: o nome da
cliente nele é texto livre.

## Clarifications

### Session 2026-11-03

- Q: Em que ordem a Fase 3 se divide? → A: **Orçamento primeiro.** 3a (esta): orçamento e formulário enviados pela
  conversa, com o orçamento ligado à ficha. 3b: origem do anúncio. 3c: linha do tempo da ficha e funil derivado.
- Q: O que a cliente recebe quando o vendedor manda o orçamento pela conversa? → A: **A mensagem pronta e o PDF
  logo depois**, como o vendedor faz à mão hoje.
- Q: De onde o vendedor manda o orçamento? → A: **Dos dois lugares**:
  - na tela do orçamento gerado, "Enviar na conversa", escolhendo a conversa;
  - dentro da conversa, "Enviar orçamento", escolhendo entre os orçamentos recentes.
- Q: Conversa sem ficha na hora de mandar o orçamento? → A: **Cria a ficha na hora.**
  - No WhatsApp, com o telefone da conversa e o nome.
  - No Instagram, que não tem telefone, o vendedor liga a uma ficha existente ou informa o telefone.

## Cenários e Verificação *(obrigatório)*

### História 1 — Enviar o orçamento de dentro da conversa (Prioridade: P1)

Na conversa aberta, o vendedor toca em "Enviar orçamento". Vê os orçamentos recentes do time (dos últimos 30 dias,
os mais novos primeiro, com busca pelo nome da cliente ou pelo local), escolhe um e confere o resumo: cliente, data,
local e valores. Ao tocar em "Enviar orçamento", saem a mensagem pronta e, em seguida, o PDF.

**Por que esta prioridade**: é o fim do copiar e colar, o portão da Fase 3.

**Verificação**: cenários 1, 2 e 5 do `verify_333.py`.

**Cenários de aceite**:

1. **Dado** uma conversa do WhatsApp com a janela aberta, **Quando** o vendedor envia o orçamento X, **Então**:
   - saem duas mensagens na ordem: o texto igual à mensagem pronta de X e o PDF de X (`Orcamento_Manto_<cliente>.pdf`);
   - o envio fica registrado: orçamento, conversa, quem enviou e quando.
2. **Dado** o mesmo pedido repetido (clique duplo, rede que reenvia), **Quando** chega, **Então** nada sai de novo.
3. **Dado** a janela de 24 h fechada, o envio travado no ambiente ou o canal desligado, **Quando** o vendedor envia,
   **Então** nada sai, nada é registrado, nenhuma ficha nasce e a tela explica o motivo com o mesmo texto do envio
   comum.

---

### História 2 — Enviar o orçamento a partir da tela do orçamento (Prioridade: P1)

Na tela do orçamento gerado (a que vem depois de "Gerar orçamento", e o "Ver" do histórico), o vendedor toca em "Enviar
na conversa". Busca a conversa pelo nome, telefone ou @usuário e escolhe. O envio é o mesmo da História 1. Depois, a
tela oferece "Abrir conversa".

**Por que esta prioridade**: o orçamento nasce na calculadora. Voltar para as Conversas e procurar o orçamento de
novo é o passo que o vendedor pula.

**Verificação**: cenário 1 (o mesmo envio, pela outra porta) do `verify_333.py`, e a tela.

**Cenários de aceite**:

1. **Dado** o orçamento X na tela, **Quando** o vendedor escolhe a conversa da Ana e envia, **Então** a conversa da Ana
   recebe as duas mensagens e o envio fica registrado.

---

### História 3 — O orçamento fica ligado à ficha da cliente (Prioridade: P1)

Todo orçamento enviado pela conversa fica ligado à ficha da cliente. Se a conversa ainda não tem ficha:
- **WhatsApp**: a ficha nasce na hora, com o telefone da conversa e o nome do orçamento (sem nome no orçamento, o nome
  do perfil). Se já existe ficha com esse telefone, com ou sem o nono dígito, a conversa e o orçamento ligam a ela.
- **Instagram**: antes de enviar, o vendedor escolhe uma ficha existente ou cria uma informando nome e telefone.

No histórico de orçamentos, o orçamento enviado ganha o selo "Enviado na conversa" com a data. Na tela do orçamento,
cada envio aparece com a conversa, quem enviou e quando.

**Por que esta prioridade**: sem a ligação, o orçamento continua sem dono, e a 3b e a 3c não têm onde se apoiar.

**Verificação**: cenários 3, 4, 8 e 10 do `verify_333.py`.

**Cenários de aceite**:

1. **Dado** uma conversa do WhatsApp sem ficha, **Quando** o vendedor envia o orçamento da "Ana Souza", **Então** a
   ficha "Ana Souza" nasce com o telefone da conversa e origem "Conversa", e a conversa e o orçamento ficam ligados a
   ela.
2. **Dado** uma ficha existente com o telefone sem o nono dígito, **Quando** o envio acontece, **Então** a conversa e o
   orçamento ligam à ficha existente, sem criar outra.
3. **Dado** uma conversa do Instagram sem ficha, **Quando** o vendedor envia sem escolher ficha, **Então** o envio é
   recusado e pede a ficha. **Quando** informa nome e telefone, **Então** a ficha nasce, liga e o envio sai.
4. **Dado** um orçamento já ligado à ficha da Ana, **Quando** ele é enviado de novo para a conversa de outra ficha,
   **Então** o envio fica registrado e o orçamento continua ligado à Ana.

---

### História 4 — Ligar, trocar ou criar a ficha da conversa (Prioridade: P2)

No cabeçalho da conversa, sem ficha, aparece "Ligar à ficha". Com ficha, além de "Ver ficha", o botão "Trocar
ficha" abre o diálogo da ficha, que também tem "Remover vínculo" (a casa não tem componente de menu; decisão da
convergência). O diálogo busca a ficha pelo nome ou telefone, ou cria uma nova (nome e telefone, com o
telefone da conversa já preenchido no WhatsApp). Se o telefone informado já é de uma ficha, a conversa liga a ela e a
tela avisa "Esta ficha já existia e foi ligada à conversa.".

**Por que esta prioridade**: a ligação automática pelo telefone (325) erra quando o número é de outra pessoa (a mãe
pede a festa pelo celular do marido) e não funciona no Instagram.

**Verificação**: cenário 7 do `verify_333.py`.

**Cenários de aceite**:

1. **Dado** uma conversa sem ficha, **Quando** o vendedor liga à ficha da Ana, **Então** a conversa mostra "Ver ficha"
   da Ana.
2. **Dado** uma conversa ligada à mão, **Quando** chega mensagem nova, **Então** a ligação automática não troca a ficha.
3. **Dado** a troca de ficha, **Quando** ela acontece, **Então** os orçamentos já enviados continuam ligados à ficha do
   envio.

---

### História 5 — Enviar o link do formulário (Prioridade: P2)

Na conversa, "Enviar formulário" mostra os formulários públicos (Pré-contrato e Corporativo). Escolhido um, o campo de
mensagem recebe o texto pronto com o link curto, para o vendedor conferir e enviar: "Oi, Ana! Para reservarmos a data,
preencha o formulário: https://app.mantoproducoes.com.br/f/pre-contrato".

**Por que esta prioridade**: o link hoje é copiado da tela de Formulários ou digitado de memória.

**Verificação**: cenário 9 do `verify_333.py`, e a tela.

---

### História 6 — "Criar evento" traz a cliente (Prioridade: P2)

"Criar evento" a partir de um orçamento ligado a uma ficha já traz a cliente no evento, além da data, do local, dos
valores e do elenco, como hoje.

**Por que esta prioridade**: é o último trecho da conversa à venda.

**Verificação**: cenário 11 do `verify_333.py`.

### Casos de borda

- **Falha da Meta numa parte**: a parte que falhou fica "não entregue". A outra parte não é desfeita, e o envio
  continua registrado. A tela não diz "enviado": avisa o que não foi entregue.
  - O texto que falhou tem o "Tentar novamente" da conversa, como qualquer mensagem.
  - O PDF que falhou sai de novo por **"Enviar só o PDF"** na conferência do orçamento, sem mandar a mensagem de
    novo para a cliente.
- **Queda no meio do envio** (rede, servidor reiniciado): repetir o mesmo pedido manda só as partes que faltaram.
- **A janela fecha no meio do envio** (raro): as partes seguintes não saem e a tela explica; as já enviadas ficam.
- **Instagram**: o texto do orçamento passa de 1.000 bytes. Ele sai em partes, quebradas entre parágrafos, na ordem, e o
  PDF vai por último.
- **Orçamento antigo sem a mensagem pronta**: o envio é recusado com "Este orçamento não tem a mensagem pronta. Use
  Recalcular e envie o novo orçamento."
- **Orçamento excluído depois do envio**: as mensagens continuam na conversa. O registro do envio vai junto com o
  orçamento.
- **Ficha excluída**: o orçamento e a conversa ficam sem ficha, sem erro.
- **Responsável**: o envio conta como resposta da equipe, com as regras da 328: assume a conversa sem responsável e
  encerra a espera.
- **Telefone inválido** ao criar a ficha: a recusa aponta o campo ("Telefone inválido. Inclua DDD (e DDI se houver).",
  o texto que a base de clientes já usa).

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: Na conversa, o vendedor DEVE poder escolher um orçamento recente do time e enviá-lo. Os recentes são os
  dos últimos 30 dias, os mais novos primeiro, com busca pelo nome da cliente ou pelo local.
- **FR-002**: Na tela do orçamento, o vendedor DEVE poder escolher uma conversa e enviar o orçamento a ela. A busca é
  pelo nome, telefone ou @usuário.
- **FR-003**: O envio DEVE mandar a mensagem pronta do orçamento e, em seguida, o PDF. No Instagram, a mensagem sai em
  partes de até 1.000 bytes, na ordem.
  - Valem as pré-condições do envio comum: canal ligado, trava do ambiente e janela (24 h; no Instagram, até 7 dias
    com a marca de resposta humana).
- **FR-004**: O mesmo pedido repetido NÃO PODE mandar nada de novo (idempotência pela chave de envio).
- **FR-005**: O sistema DEVE registrar cada envio: orçamento, conversa, quem enviou, quando e as mensagens geradas.
- **FR-006**: O orçamento DEVE ficar ligado à ficha da conversa no primeiro envio. Envios seguintes para outra ficha
  não trocam a ligação.
- **FR-007**: Conversa do WhatsApp sem ficha DEVE ganhar a ficha na hora.
  - Nome: o do orçamento, se ele ainda não tem ficha; senão (ou sem nome), o do perfil; sem os dois, o
    telefone. O orçamento da Ana reenviado para outra conversa não batiza a ficha nova de "Ana".
  - Telefone: o da conversa. Origem: "Conversa".
  - Ficha existente com o mesmo telefone (com ou sem o nono dígito) é reaproveitada; com as duas, vale a do
    telefone exato da conversa (a regra da 325).
- **FR-008**: Conversa do Instagram sem ficha DEVE exigir a ficha no envio: uma existente ou uma nova com nome e
  telefone. Sem ela, a recusa aponta o campo da ficha.
- **FR-009**: O vendedor DEVE poder ligar a conversa a uma ficha, trocar a ficha, remover o vínculo e criar uma ficha
  nova pela conversa.
  - A ligação automática pelo telefone nunca sobrescreve a escolha manual, inclusive a remoção do vínculo.
  - A troca não muda os orçamentos já ligados.
- **FR-010**: Na conversa, "Enviar formulário" DEVE oferecer os formulários públicos e inserir no campo de mensagem o
  texto pronto com o link curto do endereço público da Plataforma, editável antes do envio.
- **FR-011**: "Criar evento" a partir de um orçamento ligado DEVE trazer a ficha como cliente do evento, com a
  relação "Contratante", sem repetir a ficha que já estiver na lista.
- **FR-012**: O histórico de orçamentos DEVE mostrar o selo "Enviado na conversa" com a data do último envio. A tela do
  orçamento DEVE listar os envios (conversa, quem e quando), com o link para a conversa.
- **FR-013**: A ficha criada pela conversa DEVE aparecer com origem própria ("Conversa") no gráfico de clientes novos da
  base de clientes.
- **FR-014**: Nenhuma chamada à Meta acontece dentro de transação aberta. A falha de uma parte não desfaz a outra nem o
  registro.
- **FR-015**: Os textos novos seguem o Princípio XV.

### Entidades

- **Orçamento** (`orcamento_history`): ganha a ficha (`client_id`, → `clients`, apagada a ficha, fica vazio).
- **Envio do orçamento** (tabela nova): orçamento (apagado o orçamento, vai junto), conversa (idem), quem enviou, quando,
  as mensagens geradas e a chave de envio.
- **Ficha** (`clients`): origem nova "conversa".

### RBAC

- Enviar orçamento pela conversa, ligar/trocar/remover/criar ficha pela conversa e listar os formulários: COMERCIAL e
  SUPERADMIN (`pode_conversas`), papel real.
- Histórico e detalhe do orçamento: o gate de hoje (`_require_vendas`, COMERCIAL e SUPERADMIN); o histórico continua do
  time inteiro (301). Mandar o orçamento de outra pessoa do time é permitido, como o reenvio por e-mail, e o registro
  do envio guarda quem mandou.
- Pré-preenchimento do evento: o gate de hoje.

## Verificação (`verify_333.py`) *(obrigatório — Princípio VIII)*

Contra o `manto_local`, com disjuntor de rede e dublê do cliente da Meta (WhatsApp e Instagram), conferindo o que sai.
Login pela API, conferência por conexão separada e limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Enviar o orçamento numa conversa do WhatsApp com ficha | texto igual à mensagem pronta, depois o PDF; envio registrado; orçamento ligado à ficha | não |
| 2 | Repetir a mesma chave | nada sai de novo | não |
| 3 | Conversa do WhatsApp sem ficha; outra com ficha de telefone sem o nono dígito | ficha criada (nome do orçamento, origem "conversa") e ligada; a existente reaproveitada | não |
| 4 | Instagram: sem ficha; com ficha nova informada | 422 na ficha; depois o texto em partes ≤ 1.000 bytes, na ordem, e o PDF | não |
| 5 | Janela fechada, ambiente travado | nada sai e nada é registrado | **sim** |
| 6 | Casting envia orçamento e liga ficha | 403 | **sim** |
| 7 | Ligar, trocar e remover o vínculo à mão; mensagem nova depois | a ligação manual fica; a automática não sobrescreve | não |
| 8 | Reenviar o orçamento para a conversa de outra ficha | envio registrado; o orçamento continua com a primeira ficha | não |
| 9 | Formulários da conversa | Pré-contrato e Corporativo com o link público e o texto | não |
| 10 | Histórico e detalhe do orçamento | selo com a data do último envio; envios no detalhe | não |
| 11 | Pré-preenchimento do evento | a cliente do orçamento vem junto | não |
| 12 | A Meta recusa o PDF; "Enviar só o PDF" | o texto sai, o PDF fica "não entregue", o envio continua registrado; depois só o PDF sai | não |
| 13 | Orçamento sem a mensagem pronta; telefone inválido ao criar a ficha | 422 com o texto da spec | **sim** |
| 14 | Queda no meio (o texto saiu, o PDF não) | a mesma chave manda só o PDF | não |
| 15 | Limpeza | registros e usuários de teste apagados | — |

Conferência de tela: "Enviar orçamento" e "Enviar formulário" na conversa; "Ligar à ficha" e o menu da ficha no
cabeçalho; "Enviar na conversa" e os envios na tela do orçamento; o selo no histórico; o evento pré-preenchido. Em
desktop e 375×812.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: O vendedor manda o orçamento (mensagem e PDF) em até 3 toques a partir da conversa, sem copiar nem colar.
- **SC-002**: Todo orçamento enviado pela conversa fica ligado a uma ficha.
- **SC-003**: O evento criado a partir de um orçamento enviado já vem com a cliente.
- **SC-004**: Nenhum envio duplicado por clique repetido.

## Fora de escopo

- A origem do anúncio (3b) e a linha do tempo da ficha com o funil derivado (3c).
- Lembrete ou follow-up automático do orçamento (Fase 6).
- O orçamento com a janela fechada: o vendedor manda um modelo aprovado antes, como hoje.
- Gerar o orçamento dentro da conversa: a calculadora continua a mesma tela.
- Registrar que o formulário foi enviado (a resposta já se liga à cliente pelo telefone).

## Docs a atualizar

- `docs/01`: a coluna, a tabela nova, os endpoints, o RBAC e a origem "conversa".
- `docs/02`: Conversas, tela do orçamento, histórico e criar evento.
- `docs/03`: entrada no topo.
- `docs/04`: invariantes de Conversas e Orçamento.
- `docs/05`: se surgir dívida.
- `docs/PLANO_CRM_PROPRIO.md`: Fase 3a.

## Premissas

- **Orçamentos recentes**: os últimos 30 dias do time, no máximo 50, com busca. Orçamento mais antigo se encontra pelo
  histórico e sai pela tela dele.
- **Nome do PDF**: o mesmo do download de hoje.
- **Texto do formulário**: "Oi, {primeiro nome}! Para reservarmos a data, preencha o formulário: {link}". Sem nome
  conhecido, "Oi! Para reservarmos a data, preencha o formulário: {link}".
- **O PDF é o mesmo do download e do e-mail**, gerado na hora do envio a partir do orçamento congelado.
