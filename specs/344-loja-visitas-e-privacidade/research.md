# Pesquisa — 344

## R1. Como contar visita sem cookie
- **Decisão**: contador agregado (campanha, dia, origem) incrementado por um `POST` disparado uma vez por
  aba (`sessionStorage`), sem IP, sem identificador.
- **Por quê**: responde "quantas e de onde" sem dado pessoal — não exige aviso de cookies (só armazenamento
  da própria aba, não rastreia entre sites). O limite por IP do Flask-Limiter fica em memória.
- **Rejeitado**: Google Analytics (cookie + aviso + conta do dono); log do servidor (sem origem, some em
  dias); contar no `GET /horarios` (refetch e robôs inflam).

## R2. De onde vem a origem
- **Decisão**: `?origem=` > `utm_source` > `document.referrer` (instagram.com, facebook.com/fb.com,
  google., tiktok.com) > "direto"; o servidor reduz de novo a `{instagram, facebook, whatsapp, google,
  tiktok, email, outro, direto}`.
- **Por quê**: o WhatsApp não manda procedência; só o link com `?origem=whatsapp` separa o grupo. Os
  anúncios da Meta já acrescentam `utm_source=facebook|instagram`.
- O domínio curto `alo.mantoproducoes.com.br/<slug>` preserva a query no redirect 302 (sondado em
  16/11): os links por canal usam ele.

## R3. Base legal e aceite (LGPD)
- **Decisão**: venda = execução de contrato (art. 7º, V); novidades = consentimento (art. 7º, I),
  caixinha desmarcada, registro de data/hora + versão do texto (ônus da prova, art. 8º §2º). Dados de
  quem recebe (muitas vezes criança, art. 14) só para o serviço, nunca para o CRM.
- **Retenção**: dicas apagadas em 30 dias da data de referência (art. 15/16: término do tratamento). O
  pedido em si (valor, pagamento, contato) fica — obrigação fiscal.
- O texto do aviso é um rascunho operacional; o dono foi avisado de que um advogado deve revisar.

## R4. Cliente do CRM a partir da venda
- **Decisão**: `normalize_phone` (DDI 55) como chave; ficha nova `source="loja_virtual"`; existente só
  preenche vazios; `ensure_event_client` liga o evento; tudo num SAVEPOINT dentro do commit da venda.
- **Por quê**: o telefone do pedido está só em dígitos sem DDI; o CRM usa com DDI — sem normalizar, a
  mesma pessoa viraria duas fichas.

## R5. Limpeza das dicas no Google
- **Decisão**: `update_event` com o mesmo título/horário e a descrição sem a linha "Dicas da família";
  com `CALENDAR_SUPPRESS_EVENT_WRITES` ligada (cópia de teste), pula o Google e limpa o banco; falha do
  Google deixa o pedido para a próxima volta (nada pela metade).

## R6. Pixel
- **Decisão**: snippet oficial `fbevents.js`, carregado só depois do "Aceitar"; `fbq('init', id)` sem
  advanced matching; `Purchase` uma vez por `public_token` (marca em `localStorage`).
- **Rejeitado**: API de Conversões (servidor → Meta) — exige token de sistema do dono e mais escopo.
