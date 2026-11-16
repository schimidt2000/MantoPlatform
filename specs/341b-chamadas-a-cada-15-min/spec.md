# 341b — Um horário de chamada a cada 15 minutos

**Branch**: `341b-chamadas-a-cada-15-min` · **Created**: 2026-11-12 · **Status**: EM PRODUÇÃO desde
16/11/2026 ~20h27, push `cdfaf3ed` (`verify_341b.py` 14/14) · **Migration**: nenhuma

> Nível 2, hotfix da 341 (Papai Noel para todos). Um domínio (loja virtual), sem migration.

## O pedido

O dono, em 12/11/2026, olhando a loja do Papai Noel: os horários estavam de 10 em 10 minutos, "porém
a chamada pode durar até 10, então precisa pelo menos de 5 minutos de pausa entre uma e outra. Se a
primeira é 2, a segunda começa 2:15". Na mesma conversa: "pode colocar até as 19h".

## O que já foi feito em produção (dado, não código)

No mesmo dia, pelas funções do sistema (`gerar_slots`, `remover_slot`, `atualizar_campanha`), por
SSH com `MANTO_SEM_THREADS=1`: os 24 horários livres de 06/12 (14h00–17h50, de 10 em 10, nenhum com
pedido) viraram 20, de 15 em 15 (14h00 … 18h45; a última chamada termina 18h55); os de :00 e :30
ficaram, os outros saíram. Capacidade de vídeos 0 → 40 (entrega até 13/12, já gravada na 341).

## O que muda no código

Para o próximo "Gerar horários" da tela não voltar aos 10 em 10:

- `VIRTUAL_SLOT_INTERVAL_MINUTES = 15` (`app/constants.py`), separado de `VIRTUAL_SLOT_MINUTES = 10`,
  que continua sendo a duração da chamada (fim do evento e da sala).
- `gerar_slots` anda de 15 em 15 e **pula o horário que ficaria a menos de 15 min de outro** da
  mesma campanha (grade antiga de 10 em 10, janela vizinha); conta em `skipped`.
- Tela da campanha: botão "Gerar horários", ajuda explica os 10 + 5, e o retorno diz "pulado(s):
  já existiam ou ficariam sem a pausa de 5 min".

## Verificação

`verify_341b.py` contra o `manto_341b` (dump de produção de 12/11 02h): janela 14h–18h → 16 de 15 em
15 pela rota da tela; repetir não cria nada; grade antiga 10h00/10h10/10h20 → só nasce 10h45; vizinho
12h10 tira o 12h15; duração 10 e passo 15; papel sem acesso → 403 (deve falhar). **Com o código
antigo: 9 FALHA pelo motivo certo** (gera 24, de 10 em 10). Depois: 14/14. Tela aberta na cópia local
(gerar 14h–15h → "4 criados"; de novo → "0 criados · 4 pulados…").

Regressão no mesmo banco: `verify_310.py` **652/652** (antes 616/23 por acaso — dívida 206, quitada
aqui), `verify_340.py` 64/64, `verify_341.py` 20/20, `verify_310b.py` 12/12, `verify_205.py` 138/138
(V1.8–V1.10 passam a esperar 16 horários; V8.1–V8.2 contam só os pedidos da campanha do verify).

Carga em produção (12/11 ~20h55, só leitura): 30 visitantes simultâneos na página do Papai Noel por
45 s, ~960 aberturas por minuto, nenhum erro, p95 ≤ 0,9 s.

## Fora de escopo

Dívida 207 (remover pela tela um horário que já teve reserva expirada dá 500) — segue aberta; durante
a campanha, pausar em vez de remover.
