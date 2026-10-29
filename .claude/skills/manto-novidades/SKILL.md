---
name: manto-novidades
description: >
  Contar à equipe o que mudou no sistema depois de um deploy. Lista o que entrou na `main` desde
  o último aviso (`scripts/novidades.py`), escreve uma mensagem de WhatsApp por grupo (vendas,
  casting, ensaios, figurinos, redes sociais) no tom da casa e grava em
  `docs/novidades/AAAA-MM-DD.md` e, com o texto aprovado pelo dono, envia pelo WhatsApp Web no
  Claude in Chrome, um grupo por vez. Use quando o dono disser "avisa a equipe",
  "novidades", "manda para os grupos", "/manto-novidades", e depois de todo deploy (o gancho
  `pre-push` lembra quantas mudanças estão sem aviso). Regra de texto: constituição, Princípio XV
  ("mensagem de WhatsApp que a equipe copia").
---

# manto-novidades — contar à equipe o que mudou

## Por que existe

Push na `main` é deploy, e a equipe só descobre a mudança quando tropeça nela. Este fluxo fecha o
ciclo: toda mudança publicada vira uma frase no grupo certo, no dia do deploy ou na rodada
seguinte. O marco "até onde a equipe já foi avisada" é `docs/novidades/ULTIMO_AVISO`; o gancho
`scripts/hooks/pre-push` (instalado em `.git/hooks/pre-push`) imprime, a cada push da `main`,
quantas mudanças ainda não foram contadas.

## Passo a passo

1. **Listar.** `PYTHONUTF8=1 python scripts/novidades.py` (na raiz; em worktree, no checkout
   principal). Cada linha é um merge `merge: NNN — …` ou commit solto na `main` desde o marco,
   com a data em que entrou em produção (lida do `docs/03`) e as pistas de grupo pelos arquivos.
   `⚠` = a entrada do `docs/03` fala em interruptor ou "desligada": **não anuncie** o que o dono
   ainda precisa ligar ou configurar; deixe em "Guardado para a próxima rodada".
2. **Rascunho.** `--rascunho` grava `docs/novidades/<hoje>.md` com o esqueleto por grupo e o
   material de cada mudança (spec, "O pedido"). Se o arquivo do dia já existe, continue nele.
3. **Ler o que mudou.** Para cada mudança, leia **só a entrada dela** no `docs/03` (índice →
   `Read` com `offset`/`limit`): "O pedido" e "O que mudou" bastam. Não abra a spec inteira.
   Descarte o que é só harness ou documentação (constituição, templates, `chore`).
4. **Confirmar o nome na tela.** Todo botão, menu, selo ou página citado na mensagem vai com o
   texto exato da tela: `Grep` em `frontend/apps/internal/src` (ou `public`/`portal`) antes de
   escrever. "Solicitar cancelamento", "Editar motivo", "Produtos de tabela", "Alterar devolução".
5. **Escrever por grupo** (regras abaixo) nas seções `### <Grupo>` do arquivo, cada mensagem num
   bloco ```text pronto para copiar. A mesma mudança pode ir a mais de um grupo, com a frase
   ajustada ao papel (a comercial pede o cancelamento; o casting recebe o aviso).
6. **Mostrar ao dono** o arquivo e a tabela "Quem recebe o quê". Ele ajusta ou aprova.
7. **Enviar** pelo Claude in Chrome (seção abaixo), com o texto que o dono aprovou, ou o dono cola
   à mão. Anotar no arquivo, por grupo, "enviado em dd/mm hh:mm".
8. **Marcar.** `PYTHONUTF8=1 python scripts/novidades.py --marcar --arquivo docs/novidades/<hoje>.md`
   e commit `docs(novidades): rodada de <dd/mm>` com `docs/novidades/`. Sem o `--marcar`, a
   próxima rodada repete tudo.

## Regras de texto (constituição §XV, "mensagem de WhatsApp que a equipe copia")

- Tom de conversa da casa, português correto e com acento. Abre de forma amigável (pedido do
  dono, 29/10): "Oi, pessoal, tudo bem? Passando aqui para contar as últimas novidades do sistema.
  Aqui vai:". Fecha com "Qualquer dúvida, me chama." (para artistas: "fale com a produção"). Sem "pra", "tá", "né".
- **Fácil de entender, mas explicativo o bastante para não deixar dúvida** (pedido do dono,
  28/10). Quem lê não acompanhou o desenvolvimento e não vai abrir o sistema para descobrir o que
  a frase quis dizer. Cada mudança é um item de duas a quatro frases curtas, nesta ordem:
  1. **O que mudou**, em palavras do dia a dia ("Agora a calculadora tem um campo para o desconto
     que você negociou com a cliente").
  2. **Como era antes**, quando ajuda a reconhecer ("Antes era preciso lançar um acréscimo
     negativo").
  3. **O que fazer** e **onde**, com o nome exato da tela ou do botão.
  4. Quando a regra não é óbvia, **um exemplo** com números ou um caso real.
  Mudança que não altera o que a pessoa faz cabe numa frase só, ou fica de fora.
- Frases curtas, uma ideia por frase. Nada de sigla sem explicar (BV, DRE) para quem não usa a
  palavra no dia a dia.
- Blocos em *negrito* do WhatsApp (asterisco) por assunto, itens com "•" e uma linha em branco
  entre itens. Mensagem longa é aceitável se cada item muda algo no trabalho do grupo; corte o
  que não muda a ação, nunca a explicação do que muda.
- **Não entra**: número de feature, nome de arquivo, "migration", "endpoint", "verify",
  dívida técnica, causa técnica do defeito, e nada que esteja desligado ou dependa de o dono
  configurar. O que não está no ar não se anuncia.
- Números só quando mudam a ação: preço de tabela, cachê, prazo, data (24 e 25/12).
- Defeito corrigido vira "não acontece mais X" sem culpar ninguém.
- O texto é o que vai ser copiado: nada de "(ver docs)" ou link interno. Link só do portal ou
  da loja, quando a pessoa precisa abrir.

## Grupos e papéis

Os nomes são os dos grupos no WhatsApp (informados pelo dono em 28/10). A seção do arquivo do dia
tem o mesmo nome do grupo, para o dono achar pela busca do WhatsApp.

Nome exato no WhatsApp (conferido em 29/10): "MANTO - VENDAS", "MANTO - CASTING", "MANTO -
ENSAIOS", "* FIGURINOS *" e "MANTO - REDES SOCIAIS". Cuidado: "✨ CASTING MANTO ✨" é outro grupo,
e "MANTO - PAGAMENTOS" e "MANTO - CONTRATOS" não recebem novidades.

| Grupo no WhatsApp | Quem está (papel no sistema) | Assuntos |
|---|---|---|
| vendas | COMERCIAL | calculadora, orçamento, catálogo, clientes, formulários, cobrança, comissão, pedido de cancelamento |
| casting | CASTING | escala, painel da Home, banco de talentos, cachê e teto, e-mails e portal do elenco |
| ensaios | ENSAIO | agenda, eventos 🟧 de ensaio, painel de ensaio, EducaManto, o que muda para quem só consulta o evento |
| figurinos | FIGURINO | painel de figurino, pedidos, fotos |
| redes sociais | MARKETING | loja virtual, catálogo público, posts, painel de marketing |

- **Financeiro não tem grupo**: hoje ninguém além do dono cuida dele. Mudança só financeira
  (gastos extras, pagamentos, DRE, devolução) não vira mensagem; se ela muda o trabalho de outro
  grupo (comissão da vendedora, multa ao elenco), entra na mensagem desse grupo.
- **Não há grupo geral**: o que vale para todo mundo (navegação, arquivo, textos) entra em cada
  mensagem, com a frase ajustada ao grupo.
- **Artistas** só recebem aviso se o dono pedir (não há grupo; seria lista de transmissão).
- Superadmin recebe tudo (é o dono).

## Enviar pelo Claude in Chrome

O dono deixa o WhatsApp Web aberto no Chrome dele, já logado. Não existe envio sem ninguém
olhando: a API oficial do WhatsApp não cobre grupos de forma aberta, e automação por cima do
WhatsApp Web arrisca o número da empresa. O envio é assistido:

1. O texto de cada grupo é o que o dono aprovou no arquivo do dia. Nada que ele não viu vai.
2. Carregue as tools do Chrome numa chamada só (`ToolSearch` com
   "select:mcp__claude-in-chrome__tabs_context_mcp,…navigate,…computer,…read_page,…find,
   …javascript_tool") e use a aba do WhatsApp que já está aberta.
3. Para cada grupo: buscar pelo nome exato na caixa de pesquisa, abrir a conversa, **conferir o
   nome do grupo no cabeçalho**, colocar a mensagem na caixa de texto e **ler o que ficou na caixa**
   antes de enviar. Quebra de linha no WhatsApp Web é Shift+Enter: Enter sozinho envia pela
   metade. O mais seguro é colar o texto inteiro (área de transferência ou evento de colar na
   caixa), não digitar linha a linha.
4. Um grupo por vez; se algo sair diferente do aprovado (texto cortado, grupo errado), pare e
   avise o dono antes de seguir. Nunca contato individual, nunca grupo fora da lista.
5. Depois de cada envio, anotar "enviado em dd/mm hh:mm" na seção do grupo.

## Armadilhas

- `scripts/novidades.py` lê o `docs/03` para saber a data de produção e o sinal de "desligada".
  Entrada sem "EM PRODUÇÃO desde" aparece como "sem data": confira pelo merge na `main`.
- A spec de muita feature fica com `Status: Rascunho` (template do Spec Kit); por isso o script
  não usa esse campo.
- O gancho `pre-push` vive em `.git/hooks/` (não versionado): depois de clonar ou de criar
  máquina nova, copie `scripts/hooks/pre-push` para lá.
- Mudança que entrou por hotfix direto na `main` (sem merge) aparece pelo assunto do commit;
  `docs(...)` e `chore(...)` ficam de fora.
