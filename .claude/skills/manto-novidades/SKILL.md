---
name: manto-novidades
description: >
  Contar à equipe o que mudou no sistema depois de um deploy. Lista o que entrou na `main` desde
  o último aviso (`scripts/novidades.py`), escreve uma mensagem de WhatsApp por grupo (Comercial,
  Financeiro, Casting e Produção, Figurino, Marketing, Artistas, Todos) no tom da casa, grava em
  `docs/novidades/AAAA-MM-DD.md` e, se o dono pedir, cola no WhatsApp Web pelo Claude in Chrome,
  um grupo por vez, com OK antes de cada envio. Use quando o dono disser "avisa a equipe",
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
7. **Enviar** (pelo dono, ou pelo Claude in Chrome — ver abaixo). Anotar no arquivo, por grupo,
   "enviado em dd/mm hh:mm".
8. **Marcar.** `PYTHONUTF8=1 python scripts/novidades.py --marcar --arquivo docs/novidades/<hoje>.md`
   e commit `docs(novidades): rodada de <dd/mm>` com `docs/novidades/`. Sem o `--marcar`, a
   próxima rodada repete tudo.

## Regras de texto (constituição §XV, "mensagem de WhatsApp que a equipe copia")

- Tom de conversa da casa, português correto e com acento: abre com "Oi, pessoal!" e fecha com
  "Qualquer dúvida, me chama." (para artistas: "fale com a produção"). Sem "pra", "tá", "né".
- **Uma linha por mudança**, nesta ordem: o que mudou → o que fazer diferente → onde (nome exato
  da tela ou botão). Se a mudança não muda nada no que a pessoa faz, uma frase curta ou nada.
- Blocos em *negrito* do WhatsApp (asterisco), itens com "•". Até ~25 linhas por grupo; se
  passar, corte o que não muda a ação, nunca o que muda.
- **Não entra**: número de feature, nome de arquivo, "migration", "endpoint", "verify",
  dívida técnica, causa técnica do defeito, e nada que esteja desligado ou dependa de o dono
  configurar. O que não está no ar não se anuncia.
- Números só quando mudam a ação: preço de tabela, cachê, prazo, data (24 e 25/12).
- Defeito corrigido vira "não acontece mais X" sem culpar ninguém.
- O texto é o que vai ser copiado: nada de "(ver docs)" ou link interno. Link só do portal ou
  da loja, quando a pessoa precisa abrir.

## Grupos e papéis

| Grupo | Papel no sistema | Assuntos |
|---|---|---|
| Comercial | COMERCIAL | calculadora, orçamento, catálogo, clientes, formulários, cobrança, pedido de cancelamento |
| Financeiro | FINANCEIRO + dono | gastos extras, pagamentos, comissões, planilha, DRE, PIX, devolução, página Cancelamentos |
| Casting e Produção | CASTING, ENSAIO | escala, painel da Home, banco de talentos, cachê e teto, e-mails ao elenco |
| Figurino | FIGURINO | painel de figurino, pedidos, fotos |
| Marketing | MARKETING | loja virtual, catálogo público, posts, painel de marketing |
| Artistas (portal) | talentos (lista de transmissão) | só o que muda no portal ou nos e-mails deles |
| Todos | equipe inteira | navegação, arquivo, textos, o que vale para qualquer papel |

O nome real de cada grupo no WhatsApp é informado pelo dono; quando souber, grave em
`docs/novidades/GRUPOS.md` (grupo → nome no WhatsApp → quem está). Superadmin recebe tudo.

## Enviar pelo Claude in Chrome (semiautomático)

Não há envio sem ninguém olhando: a API oficial do WhatsApp não cobre grupos de forma aberta, e
automação por cima do WhatsApp Web arrisca o número da empresa. O que existe é o envio assistido:

1. Só quando o dono pedir ("manda", "envia para os grupos"), com o Chrome aberto em
   `web.whatsapp.com` já logado. Carregue as tools do Chrome numa chamada só (`ToolSearch`
   "select:mcp__claude-in-chrome__tabs_context_mcp,…navigate,…computer,…read_page,…find").
2. Para cada grupo: localizar pela caixa de pesquisa, abrir a conversa, **conferir o nome do
   grupo no cabeçalho**, colar a mensagem na caixa de texto (quebra de linha com Shift+Enter) e
   ler o que ficou na caixa antes de enviar.
3. **Um OK do dono por grupo antes do Enter**, a menos que ele tenha dito, na mesma mensagem,
   "manda para todos" com a lista dos grupos. Nunca para contato individual, nunca fora do
   expediente sem pedido, nunca a partir de texto que o dono não viu.
4. Depois de cada envio, anotar no arquivo do dia "enviado em dd/mm hh:mm" na seção do grupo.

Se o dono preferir enviar à mão, entregue o arquivo e a correspondência "grupo ← seção".

## Armadilhas

- `scripts/novidades.py` lê o `docs/03` para saber a data de produção e o sinal de "desligada".
  Entrada sem "EM PRODUÇÃO desde" aparece como "sem data": confira pelo merge na `main`.
- A spec de muita feature fica com `Status: Rascunho` (template do Spec Kit); por isso o script
  não usa esse campo.
- O gancho `pre-push` vive em `.git/hooks/` (não versionado): depois de clonar ou de criar
  máquina nova, copie `scripts/hooks/pre-push` para lá.
- Mudança que entrou por hotfix direto na `main` (sem merge) aparece pelo assunto do commit;
  `docs(...)` e `chore(...)` ficam de fora.
