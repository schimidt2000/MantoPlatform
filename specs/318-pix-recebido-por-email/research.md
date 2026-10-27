# Research — 318 PIX recebido por e-mail

Decisões técnicas da Phase 0. Fatos de código citados contra o HEAD `5781993c`.

## R-01 Fonte: IMAP da caixa joao@mantoproducoes (não Gmail API, não webhook de e-mail)

- **Decision**: ler por IMAP, só leitura (`EXAMINE` + `BODY.PEEK[]`), a pasta "Todos os e-mails" de
  `MAIL_USERNAME` (default real `joao@mantoproducoes.com.br`, `app/config.py:249`) com `MAIL_PASSWORD` — a mesma
  credencial do varredor de e-mails devolvidos (feature 219, `app/integracoes/imap_client.py`). A Prime chega pela
  regra de encaminhamento criada em 22/10 (`from:(no-reply@inter.co) subject:("Pix recebido")` →
  joao@mantoproducoes).
- **Rationale**: zero credencial nova (Princípio XIV), o sistema já tem esse acesso, o padrão de leitura e de
  idempotência já existe e roda em produção. Conferido em 22/10: a caixa guarda cópia (337 avisos desde 01/06).
- **Alternatives**: Gmail API com `gmail.readonly` no token OAuth da agenda (escopo restrito, reconsentimento, token
  com acesso amplo); caixa dedicada pix@ (licença nova; o dono escolheu a caixa existente); webhook de e-mail de
  entrada (terceiro novo); trocar o e-mail cadastrado no Inter (afeta fatura/login).

## R-02 Formato do aviso e parser

- **Decision**: parser puro `ler_aviso_inter(raw: bytes) -> AvisoPix | None` que junta o texto das partes
  `text/plain`/`text/html` (tags removidas, espaços normalizados) e casa
  `Você recebeu um Pix no valor de R$ <valor> de <nome>, na conta <número>.`; devolução casa
  `Você recebeu a devolução de um Pix, no valor de R$ <valor>, na conta <número>` (tipo `devolucao`, ignorado).
  Hora = cabeçalho `Date` convertido para horário de parede de São Paulo (naive, como `start_at`). Identidade =
  cabeçalho `Message-ID`. Autenticidade = `Authentication-Results` com `dkim=pass header.i=@inter.co` (ou `header.d`)
  do servidor do Google que recebeu.
- **Rationale**: o texto é uma frase fixa ("Olá, JOAO/PRIME Você recebeu um Pix no valor de R$ 2.200,00 de <nome>, na
  conta <número>."); DKIM sobrevive ao encaminhamento do Gmail (corpo intacto). Falha de formato vira contagem de
  "não entendidos", nunca exceção silenciosa.
- **Prova (22/10, só leitura, só contagens)**: o rascunho do regex rodado sobre todos os avisos da caixa desde 01/06:
  **338 de 338 entendidos**, 338 com `Message-ID`, 338 com `dkim=pass header.i=@inter.co`; todos `text/html` puro
  (sem parte texto); todos da conta MEI (a Prime passa a chegar com o filtro de 22/10).
- **Alternatives**: extrair do `snippet`/HTML com seletores (frágil); ler extrato CSV (manual, fora do pedido).

## R-03 Idempotência e reprocessamento

- **Decision**: `pix_recebidos.message_id` UNIQUE; inserção com "já existe → pula". Janela de busca IMAP
  `SINCE hoje−3d` a cada rodada (reler é inofensivo). PIX `sem_venda` com `recebido_em` nos últimos 7 dias é
  reavaliado a cada rodada (decisão do dono, clarify); depois disso, nunca mais.
- **Rationale**: mesmo molde do `EmailBounce.message_id` (219) e do `transaction_nsu` UNIQUE (310). O Inter não manda
  E2E; `e2e_id` fica nullable UNIQUE para fontes futuras.

## R-04 Rodada única entre workers

- **Decision**: thread `pix-email` em `create_app`, intervalo `PIX_EMAIL_SWEEP_INTERVAL=900`, claim atômico
  `UPDATE site_settings SET pix_email_sweep_at=now WHERE pix_email_sweep_at IS NULL OR pix_email_sweep_at < now−intervalo`
  com `rowcount == 1` (molde de `_claim_auto_sync`/`virtuais_ops.claim_sweep`). Ligada por
  `PIX_EMAIL_SWEEP_ENABLED` (default `"false" if _suppress_mail() else "true"`, igual ao bounce) **e** pelo
  interruptor `site_settings.pix_email_ativo` (nasce `False`; o Superadmin liga depois do ensaio).
- **Rationale**: gunicorn sobe 3 workers × thread; o claim é o padrão da casa. Dois interruptores: o de env protege o
  `manto_local` (espelho com credencial real), o de tela é a decisão do dono.

## R-05 Regra de vínculo

- **Decision**: núcleo puro em `app/financeiro/pix_ops.py`:
  1. Fora: devolução; pagador ∈ `pix_pagadores_proprios` (normalizado), exceto "Prime Dreams" na conta MEI (R-07).
  2. Candidatas: vendas da cobrança (`cobranca_ops`, evento líder, fora `motivo_fora_da_venda`, saldo > `FOLGA_COBRANCA`).
  3. Valor forte (±R$ 0,01): `saldo`; `valor/2` se `sinal_pendente`; `EventInstallment` com `received=False`;
     `valor` se nada recebido.
  4. Nome: tokens normalizados (NFKD sem acento, minúsculas, sem stopwords `ltda me eireli sa de da do das dos e`,
     tokens ≥ 3 letras); bate com ≥ 2 tokens em comum, ou 1 token se o nome do cliente tem 1 só, ou
     `difflib.SequenceMatcher` ≥ 0,85 no nome inteiro — contra contratante (`vendas_ops.contratante_name`),
     `Client.company` e demais `EventClient`.
  5. Já pagou antes: existe `pix_recebidos` ligado (auto/confirmado) com o mesmo `pagador_norm` a evento do mesmo grupo
     ou do mesmo cliente.
  6. Auto ⇔ exatamente 1 candidata com valor forte ∧ (nome ∨ já pagou) ∧ autenticado. "Para conferir" ⇔ ≥ 1 candidata
     com valor forte, ou com (nome ∨ já pagou) ∧ valor ≤ saldo; top 3 ordenadas (valor forte > já pagou > nome > data
     do evento mais próxima). Senão `sem_venda`.
- **Rationale**: decisão do dono "valor + mais um sinal". O cruzamento de 21/10 mostrou que só 51% dos pagadores têm o
  nome da cliente, logo o valor é a chave e o nome desempata; "já pagou antes" aprende com cada confirmação sem
  tabela nova.
- **Alternatives**: tabela de apelidos pagador→cliente (redundante com o histórico de `pix_recebidos`); valor único
  bastando (rejeitado pelo dono).

## R-06 Onde o pagamento é gravado

- **Decision**: sempre por `cancel_ops.gravar_comprovante_no_grupo` (`app/calendar/cancel_ops.py:2989`), que trava o
  grupo, recusa o cancelado para não-Superadmin e chama `reaplicar_por_dinheiro`. Ganha o modo "origem PIX": aceita
  `arquivo=None` quando `origem='pix_email'`, grava `conta_id`/`origem`. Recebido continua sendo a soma de
  `event_payments` — nenhuma das cópias da soma (`comprovantes_por_evento`, `received_map`, `total_recebido`,
  financeiro, audit agent) precisa mudar.
- **Rationale**: Princípio I/IV; criar pagamento por fora pularia a trava e o recálculo da 306.
- **Alternatives**: somar PIX fora de `event_payments` (6 lugares a mudar, risco de divergência); gerar PDF do
  aviso para satisfazer `file_path NOT NULL` (arquivo falso, peso em disco).

## R-07 "Prime Dreams" no Inter MEI

- **Decision**: (a) se o valor = um `pix_recebidos` da conta Prime nos 3 dias anteriores, ou = soma de 2–3 deles
  (busca exaustiva; a Prime tem ≈3–9 PIX/mês), estado `conta_propria` (motivo "repasse da Prime"); (b) senão,
  `para_conferir` com `tipo_sugestao='repasse_infinitepay'` (só FINANCEIRO/SUPERADMIN), candidatas = vendas com
  `payment_method='cartao'` (ou pedido InfinitePay) e saldo, onde repasse ∈ [0,88; 1,00] × soma dos saldos de 1–3
  vendas; nunca automático. Confirmação grava, por venda, o pagamento do saldo (valor cobrado) e anota a taxa no PIX.
- **Rationale**: decisão do dono (repasse manual que "varia"; comercial sem trabalho). O mesmo nome serve aos dois
  repasses, e só o da InfinitePay é dinheiro ainda não visto.

## R-08 Conta que recebeu

- **Decision**: tabela `contas_recebimento` semeada na migration com 4 linhas **sem número**; o Superadmin preenche
  `numero_conta` na configuração. Aviso com número desconhecido → `conta_id NULL` + contagem "conta não cadastrada".
  `event_payments.conta_id` (nullable) preenchido pelo PIX e, opcionalmente, no comprovante manual.
- **Rationale**: número de conta não vai para o git; a conta do MEI é a pergunta do contador.

## R-09 Ator "sistema"

- **Decision**: `actor: User | None` no núcleo de comprovante; `None` = "Sistema" (nome e papel), como já fazem
  `sumico_ops.py:243-253` e a sincronização (`routes.py:2371-2378`). Os dois pontos de `reaplicar_por_dinheiro` que
  leem `actor.roles`/`actor.name` (`cancel_ops.py:2940`, `2983-2986`) passam por um ajudante. `EventLog` gravado
  direto com `actor_name="Sistema (PIX · <conta>)"`.
- **Rationale**: a thread não tem `current_user`; `_log_anexo` (`agenda_write.py:1813`) depende dele.
- **Alternatives**: usuário técnico "sistema" no banco (papel novo/semente, login inexistente; mais superfície).

## R-10 Ensaio antes de ligar

- **Decision**: `ensaio_318.py` lê a caixa real só leitura desde 01/06, roda `pix_ops` contra o `manto_local` dentro
  de transação com `rollback` no fim, compara com `receitas_entradas_classificadas.csv` (gabarito de 21/10; caminho
  por argumento, fora do repo) e imprime só contagens (auto certo/errado, para conferir, ignorado, não entendido).
  Critério: zero auto errado.
- **Rationale**: SC-001; prova a regra com 4,7 meses de dados reais sem escrever nada.
