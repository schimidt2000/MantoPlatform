# 356 — O cachê do elenco não some nem muda por fora do card do Casting

**Branch** `356-cache-nao-se-perde` · **Created** 2026-11-19 · **Status** pronto, sem push ·
**Migration** nenhuma · Nível 2 (correção na Agenda, um domínio)

## O pedido

O dono, em 19/11, sobre o evento 1516 ("(SHOW) A FLORISTA + RAPOSA + GAMBA + CERVO", 12/12, Imperatriz):
"eu já havia mudado os valores desse evento para 850 anteriormente, aí agora fui comunicado que o valor
estava errado, mas acho que no log não mostra direito. Não é a primeira vez que acontece algo assim."
Depois da investigação: "Pode corrigir, por favor".

## O que a investigação achou (produção, só leitura, 19/11)

* O 850 **nunca chegou ao servidor** antes de 19/11 10:56. O log está certo: o Matheus escalou em 12/11
  (600 e 450) e ninguém mexeu no evento até as dez linhas do dono às 10:56. A linha "Limite da vaga …
  autorizado em R$ 850,00" de 19/11 prova que o teto nunca tinha sido 850. O "Editar tudo" nunca foi
  usado no 1516, e as vagas são as originais (4610–4616).
* Em 745 vagas de eventos desde outubro, o último cachê do log bate com o gravado em todas. Nenhuma vaga
  tem o cachê apagado.
* Causa mais provável: o cachê digitado no card e **não salvo**. Cada card tem o próprio "Salvar", e o
  valor digitado morava só no estado do componente. Trocar de aba (a Produção desmonta), ir para outra
  tela ou fechar o app apagava o valor sem aviso.
* Três brechas, nenhuma com vítima até agora:
  1. **"Editar tudo" apaga o cachê.** A Comercial sem Casting não recebe `cache_value` na leitura
     (`show_casting`), a tela devolvia `null`, e `_reconcile_characters` gravava `null` em toda vaga.
     Quem via o cachê gravava qualquer valor no formulário, acima do teto e sem linha no log.
     Comprovado pelo verify no código de antes: os três cachês viram `None`.
  2. **O card perde o que foi digitado** sem avisar.
  3. **"Atribuído em" é regravado a cada "Salvar"**: o card dizia "Atribuído em 19/11" para quem foi
     escalado em 12/11, e o dono leu isso como "a escala foi refeita".

## O que muda

* **Backend.**
  * `_reconcile_characters` (`app/calendar/event_ops.py`) só mexe no cachê de quem o vê
    (`pode_ver_cache`, a mesma `show_casting` da leitura, com o "Ver como"). Vazio ou igual ao gravado
    não é alteração.
  * Quando muda, passa por `casting_ops.aplicar_cache_do_formulario`: o limite do card
    (`teto_ops.teto_efetivo`, com a regra da troca de pessoa) e o teto autorizado do Superadmin. Grava
    a linha "Atualizou cachê de X como Y para ZR$ … (formulário completo)" no log do evento.
  * `assign_role` só regrava `assigned_at` quando a pessoa da vaga muda, ou quando a vaga tem pessoa e
    não tem data.
* **Formulário completo.**
  * Quem não vê o cachê não vê o campo (`ElencoBlock cacheOculto`).
  * O PATCH só leva `cache_value` da vaga em que a pessoa alterou o campo (`CharacterUpdateInput`).
    Assim o formulário aberto antes não desfaz o que o Casting salvou pelo card depois.
* **Card do Casting.**
  * O que foi digitado e não salvo vira rascunho no `localStorage` (`lib/rascunhoDoCasting.ts`). O
    rascunho só vale enquanto a vaga no servidor está como estava quando a digitação começou, e vence
    em 7 dias.
  * O card fica com borda dourada e mostra "Alteração não salva. Descartar". A seção mostra "N vagas
    com alteração não salva. Use o Salvar de cada card."
  * Fechar ou recarregar a aba com rascunho pede confirmação ao navegador.
  * O campo que a pessoa não alterou acompanha o valor novo do servidor. Antes o card ficava com o
    número velho marcado como alterado, e um "Salvar" desfazia o de outra pessoa.

## Verificação

`specs/356-cache-nao-se-perde/verify_356.py`: 12/12 contra o dump de produção de 19/11 02h, num
Postgres temporário na porta 5435 (o serviço local estava parado e ligar pede administrador). O mesmo
script contra o código da `main` deu 4/12: os cenários 1–7 e 9 falham como esperado.

1. A Comercial salva o "Editar tudo" com `null`: os cachês ficam.
2. A Comercial manda cachê pela API: ignorado, sem log.
3. O Superadmin vendo como Comercial: os cachês ficam.
4. O Superadmin acima do teto pelo formulário: grava, com teto autorizado e as duas linhas no log.
5. Comercial+Casting pelo formulário: acima do teto não muda; dentro, grava com log como "Casting".
6. Formulário com o campo intocado não desfaz o valor do card.
7. Reenvio dos mesmos valores: nenhuma linha nova.
8. A Comercial lê o elenco sem cachê.
9. Cachê novo pelo card: "Atribuído em" fica.
10. Troca de pessoa: "Atribuído em" vira hoje.
11. Vaga antiga com pessoa e sem data ganha a data.
12. Limpeza.

**Tela aberta** (Vite e Flask da worktree contra o mesmo Postgres temporário, Google dublado):

* **Rascunho.** 850 digitado no card da Florista do 1516: o aviso aparece no card e na seção. Troca
  de aba, ida à Agenda e volta: o 850 continua com os dois avisos.
* **Salvar.** Grava 850 e o teto autorizado, mantém "Atribuído em 12/11" e apaga o rascunho.
* **Descartar.** Volta ao valor salvo.
* **Celular.** Em 375 px, sem rolagem lateral; aviso em 14 px, "Descartar" em 12 px.
* **"Editar tudo" como Comercial.** O bloco de personagens aparece sem campo de cachê. O PATCH sai
  sem a chave `cache_value`, e o banco fica com 850/450/450/450.

Typecheck das três SPAs limpo; `ruff check` limpo nos arquivos tocados (`ruff format` só no verify,
arquivo novo).

## Fora de escopo (viraram dívida no `docs/05`, 238–241)

* Todo "Salvar" do card põe a vaga em "A pagar" (`payment_status = "nao_pago"`), mesmo sem trocar a
  pessoa (238).
* Criação de evento: o cachê digitado entra sem teto e sem log, e a Comercial vê o campo (239).
* O formulário completo não manda ao artista confirmado o aviso de cachê alterado que o card manda (240).
* A navegação dentro do app com rascunho não pergunta, porque o `BrowserRouter` não tem `useBlocker`.
  O rascunho fica e volta com o aviso. No iPhone não existe `beforeunload` (241).
