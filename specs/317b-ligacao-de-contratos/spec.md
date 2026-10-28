# 317b — O contrato da ClickSign acha a venda por outros sinais

**Branch**: `317b-ligacao-de-contratos` · **Created**: 2026-10-28 · **Status**: pronta · **Migration**: nenhuma

## O pedido

Na madrugada de 28/10 o token da ClickSign entrou no Render e a simulação desde 01/06 deu 246 contratos: 175 ligados
sozinhos e **57 "a conferir"**. O dono: "será que podemos pensar um pouco mais para ver sobre esses 57 a conferir?
Tem alguma outra ligação que funciona?". Depois de ver a análise: "pode seguir, liga os cancelados à venda cancelada".

## O que a análise dos 57 mostrou (só leitura, em produção)

- **22 eram envelopes cancelados na própria ClickSign** — negócio que não fechou ou contrato refeito. Não há o que
  conferir: não foram assinados e não viram cobrança.
- Nos outros 35, o evento na agenda **quase nunca tem o telefone de quem assina**: está sem cliente, ou ligado a uma
  ficha duplicada sem o telefone ("Miriam" com o telefone × "Miriam Scanferla" com o evento). Em 23 deles o
  **formulário da cliente tem o telefone e a data certos, mas não está ligado a evento nenhum**.
- O título do evento lista personagens ("SNOOPY + CHARLIE") e o contrato diz o tema ("Arraiá com o Snoopy"): o texto
  inteiro não cabe um no outro, a palavra sim.
- Datas digitadas um dia fora (contrato 12/07 × festa 13/07) e festa remarcada (formulário de 04/10 ligado ao evento
  de 11/10).
- 2 contratos assinados de vendas canceladas (a venda certa, só que cancelada).

## O que muda

Em `sincronizar_ops._vincular`, quando data + telefone não decidem (`escolher_candidato` sem venda única):

1. **Envelope cancelado na ClickSign sem venda → `fora`** (sai de "A conferir"). Com venda única por data + telefone
   ele continua ligando, como antes (histórico do documento vigente).
2. **Venda cancelada certa → liga a ela** (decisão do dono, 28/10: o contrato assinado embasa a multa). O PDF não
   entra no evento cancelado (312) — fica `anexo_pendente`, como no cenário 32 da 317. Ligar **à mão** a venda
   cancelada continua recusado (trava da 312 no núcleo).
3. Para "sem candidato" e "sem telefone", nesta ordem, **só venda viva única liga**:
   - mesmo telefone (do nome ou de quem assina) com a data a **um dia**;
   - **formulário** do mesmo telefone e da mesma data **já ligado a um evento** (festa remarcada);
   - **e-mail** no lugar do telefone, contra o e-mail da ficha e do formulário da venda do dia;
   - **tema por palavra** (`contratos_ops.tema_por_palavra`): a única venda do dia com uma palavra do tema no título
     ou no tema do formulário, sem as palavras que não dizem a festa (ligação, cor, figurino, "festa", "aniversário",
     "turma", razão social). Dia sem venda nenhuma: procura no dia anterior e no seguinte.
4. **Empate** pelo telefone: além do texto inteiro (317), a palavra desempata.

Nada muda no que a comercial desligou, ligou à mão ou descartou (FR-005): só documento novo ou "a conferir" automático
é reavaliado. O próximo `clicksign-sincronizar --desde 2026-06-01 --aplicar` reavalia os que já estão a conferir.

`verify_317.py` muda em três pontos, de propósito: o cenário 6 (a venda cancelada certa agora liga), o 9 (ela sai de
"A conferir") e o 18 (a trava de ligar à mão a cancelada se prova com outro documento).

## Verificação

`verify_317b.py` (12 cenários, datas em 2028 para não depender do espelho): 12/12 com a correção e **2/12 no código
antigo** (caem os 10 dos sinais novos). `verify_317.py` 36/36. Ensaio em produção, simulação com o código novo contra
os 246 envelopes reais, conferido envelope a envelope antes do merge (ver `docs/03`).

## Fora de escopo

- Ligar formulário solto ao evento e juntar fichas duplicadas — a causa de fundo; fica registrada como dívida.
- Personagem × tema (Patrulha Canina × "SKYE + MARSHALL"): o catálogo não tem esses temas com esses nomes.
- Mudar a tela "A conferir" ou as sugestões dela.
