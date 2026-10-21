# 299b — A mensagem de cobrança se copia a qualquer momento

**Branch**: `299b-cobranca-a-qualquer-momento` · **Created**: 2026-10-21 · **Status**: EM PRODUÇÃO
desde 21/10/2026 ~18:17 · **Migration**: nenhuma

## O pedido

O dono: "quero que tire o bloqueio de poder copiar o texto de cobrança de 2 dias. Para poder
copiar/cobrar em qualquer momento".

Desde a 299, o item "💰 Cobrança" do menu do evento só ficava ativo a partir do vencimento do saldo
(data combinada, 1ª parcela descoberta ou, na falta delas, **2 dias antes do evento**). Antes disso
ele aparecia cinza com "Disponível apenas na data limite de pagamento ou em atraso", e o Comercial
não conseguia cobrar antes.

## O que muda

- `cobranca_ops.pode_copiar_cobranca` deixa de olhar a data: sai `vencimento is not None` e
  `vencimento <= hoje`. O `hoje` fica na assinatura (o chamador em `agenda_read` não muda).
- As outras travas continuam, porque nelas não há o que cobrar ou quem cobra é outro evento:
  - só o principal do grupo, ou o evento avulso (no outro evento do grupo segue "A cobrança deste
    grupo está no evento principal");
  - fora: cancelado, compromisso interno, ensaio, loja virtual (`motivo_fora`);
  - cortesia ou permuta, agora também de forma explícita (`not venda.cortesia`) — antes vinha só
    pelo `motivo_fora`;
  - sem valor, valor simbólico, quitada (saldo abaixo de R$ 1,00).
- O título do item desativado passa a dizer "Sem valor em aberto para cobrar".
- A mensagem não muda: antes do vencimento ela já diz "Consta um valor em aberto de R$ X com
  vencimento em DD/MM/AAAA.", que serve como lembrete.
- `docs/01` §cobrança: "a partir do vencimento" vira "a qualquer momento (299b)".

## Verificação

`specs/299b-cobranca-a-qualquer-momento/verify_299b.py` (objetos em memória, nada gravado):

1. **Deve falhar na `main` antiga**: venda com saldo e vencimento daqui a 10 dias libera.
2. **Deve falhar na `main` antiga**: venda com saldo e sem vencimento libera.
3. Vencida ou vencendo hoje continua liberando.
4. Quitada (e a folga de R$ 1,00) continua travada.
5. Cortesia, sem valor, valor simbólico e venda fora continuam travados.
6. O outro evento do grupo continua travado.
7. **Deve falhar na `main` antiga**: o JSON do detalhe (`_compute_cobranca`) leva `enabled: true`
   antes do vencimento.

Na `main` antiga: 4/7 (caem 1, 2 e 7). Depois do núcleo: 7/7. O `verify_299.py` inteiro segue
17/17. Mais o typecheck do `internal` e a tela aberta (o item ativo num evento com saldo e
vencimento no futuro).

## Fora de escopo

- A lista de Cobranças da Home, as cores e os selos ("vence em N dias", "atrasado") não mudam: a
  data de vencimento continua existindo, só não trava mais o botão.
- "💸 Cobrar reembolsos" já não tinha trava de data.
