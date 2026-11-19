# 341c — Horário indisponível à mão (e continua aparecendo na loja)

**Branch**: `341c-horario-indisponivel` · **Created**: 2026-11-19 · **Status**: EM PRODUÇÃO desde 19/11/2026 ~11h58, merge `556ab3ad` (`verify_341c.py` 28/28) ·
**Migration**: nenhuma (`virtual_campaign_slots.status` é texto; entra o valor `indisponivel`)

> Nível 2, ajuste da loja (205/341). Um domínio, sem migration.

## O pedido

O dono, em 19/11/2026, com a divulgação do Papai Noel no ar: "nessa tela eu queria um botãozinho ao
lado do excluir para deixar o horário indisponível manualmente. Tem algumas pessoas que estão
reservando no boca a boca comigo e já quero colocar como indisponível. E é importante o horário não
sumir, e sim mostrar como indisponível". Na mesma mensagem: "Eu exclui alguns manualmente sem querer,
consegue voltar eles?" — 7 horários livres removidos às 13h45 (AuditLog), devolvidos no mesmo dia por
`gerar_slots`.

Contexto: antes ele cogitou mostrar horários livres como reservados para dar sensação de movimento; foi
avisado de que isso é publicidade enganosa (CDC, art. 37). Esta feature é a versão honesta: o horário
indisponível de verdade (reservado fora do site, ou bloqueado) aparece como indisponível.

## O que muda

- Status novo do horário: `indisponivel`. Só `livre` (sem pedido) vira `indisponivel`, e só
  `indisponivel` volta a `livre` — reservado, em pagamento ou vendido não muda por aqui. Trava a linha
  do horário (`FOR UPDATE`), como a reserva: o clique do dono e a reserva de uma família no mesmo
  instante não passam os dois.
- `PATCH /api/virtuais/horarios/<id>` `{indisponivel: true|false}` — Comercial e Superadmin; `409` com
  o motivo quando o horário não pode mudar.
- **Pagamento atrasado num horário marcado à mão vira devolução.** A família reserva, abandona, a
  reserva expira, o dono marca o horário para a reserva combinada fora do site — e o pagamento dela
  chega depois: `decidir_pagamento` passa a tratar `indisponivel` como horário tomado (antes, sem pedido
  dono, ele venderia por cima do bloqueio).
- A loja mostra **todos** os horários futuros do dia: os livres para escolher e os indisponíveis
  (vendidos, em pagamento ou marcados à mão) riscados, sem clique. A API pública ganha
  `indisponiveis: [{start_at}]` ao lado de `slots` (que continua só com os livres — a página antiga em
  cache não muda de comportamento). Sem id e sem dizer o motivo.
- Tela da campanha: ao lado da lixeira, "Marcar como indisponível" (cadeado) e, no indisponível,
  "Liberar horário"; o selo diz "indisponível"/"em pagamento"/"vendido". **Remover pede confirmação**
  — foi a falta dela que apagou 7 horários. Horário indisponível também pode ser removido (não tem
  família do outro lado).

## Verificação

`verify_341c.py` contra um espelho do dump de 19/11: marcar e liberar pela rota; a loja lista o
indisponível em `indisponiveis` e não em `slots`; reservar o indisponível → `409` e nada gravado;
vendido e em pagamento não mudam (`409`); vendido também aparece riscado; remover o indisponível;
papel sem acesso → `403` (deve falhar); pagamento atrasado num horário marcado → devolução, horário
segue indisponível. Regressão no mesmo espelho: `verify_341b` 14/14, `verify_310` 652/652, `verify_340` 64/64, `verify_341` 20/20, `verify_344` 57/57, `verify_205` 138/138. Antes do código: 19 FALHA pelo motivo certo (o cenário 10 mostrou o código antigo vendendo por cima do bloqueio).
Telas: campanha (botões, confirmação) e loja em 375 px (riscados).

## Fora de escopo

Motivo do bloqueio, nome de quem reservou fora do site e cobrança dessas reservas — o horário só fica
indisponível. Botão "trocar horário" de pedido pago.
