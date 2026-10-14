# 298b — a idade do aniversariante e a assessoria do WhatsForm não chegavam ao cadastro do evento

**Branch**: `298b-sinonimos-do-formulario` · **Created**: 2026-10-14 · **Status**: Pronto · **Migration**: nenhuma

## O pedido

Fato 5 da triagem do backlog de setembro (`docs/PLANO_BACKLOG_SETEMBRO.md`), corrigido pela
recontagem em produção de 29/09: das respostas desde 01/06, perdem-se no cadastro do evento a idade
do aniversariante (70 respostas, chave `idade_a_completar_do_aniversariante`) e o telefone da
assessoria (36, `gostaria_que_a_confirmacao_do_evento_seja_com_assessoria_se_sim_digite_o_telefone`).
A 298 adivinhou o slug (`idade_do_aniversariante`, que nunca existiu) e não tinha sinônimo para a
assessoria. Plano: `docs/backlog/1d-sinonimos-do-formulario-298b.md`.

## O que muda

`app/formularios/pre_evento_ops.py`, `SINONIMOS`: a tupla `"idade"` troca o palpite pelo slug real
(a chave nativa continua primeiro, e vence); a tupla `"assessoria"` ganha o slug do WhatsForm; o
comentário da constante diz como achar slug novo. Nada de tela, endpoint ou migration.

## Decisões do dono (06/10/2026)

- 1d-Q1 = A: "como terá uma pergunta nova ela deve agir como as outras. Aparece normal nas respostas
  do formulário."
- 1d-Q2 = A: a resposta de pergunta criada no editor fica só nas respostas do formulário, não vai ao
  cadastro do evento. Registrado no contrato da 298 (`contracts/pre-evento.md`).

## Verificação

`verify_298b.py` contra o `manto_local`: 4/5 antes do conserto (`verify_298b_primeira_falha.txt`: a
idade some) e 5/5 depois (`verify_298b_saida.txt`), com o "deve falhar" do Financeiro. Regressão:
`verify_298` 17/17, zero chamadas ao Google. Ruff limpo.

## Fora de escopo

- Coluna de aniversariante, normalizar a idade, sugerir nos eventos agendados: 4a.
- Filtrar "por onde as pessoas vieram" a partir das respostas do formulário (pedido do dono junto da
  Q2): 6a e 6b.
- Script retroativo: nenhum evento futuro nasceu de resposta WhatsForm com idade.
